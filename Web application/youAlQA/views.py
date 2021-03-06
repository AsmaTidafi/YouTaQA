from django.shortcuts import render
from .forms import *
from django.core import serializers
from django.http import JsonResponse
import sys
from django.conf import settings
import lucene
from org.apache.lucene.search.similarities import *
from search import Searcher
import torch
import numpy as np
from transformers import BertForSequenceClassification
from transformers import BertTokenizer
from torch.utils.data import TensorDataset
from torch.utils.data import DataLoader, SequentialSampler
from transformers import BertTokenizer, BertForQuestionAnswering
from django.http import HttpResponse


def home(request):
    form = searchForm()

    return render(request,'index.html', {'form': form})


def answerPOST(request):
    """
    The work done here when receiving a POST request
    """
    if request.is_ajax() and request.method=="POST":
            form = searchForm(request.POST)
            if form.is_valid():
                instance = form.cleaned_data
                #pick up the question
                qst = instance.get("question")
                srobj=settings.SEARCHOBJECT
                lucene.getVMEnv().attachCurrentThread()
                #launch a search using the search engine
                result = srobj.multiFieldsSearch(qst, BM25Similarity())
                content = ""
                list=['']
                #create a list that contains in the first node the question and then the search results
                list.append(qst)
                list.pop(0)
                j=0
                for i in range(len(result)):
                    hitDoc = srobj.searcher.doc(result[i].doc)
                    content = hitDoc.get("content_section")
                    list.append(content)
                    id = hitDoc.get("id_section")
                if not (len(list) == 1) or not(len(list) == 0):
                    # Convert the list into an array
                    qst = list.pop(0)
                    inputs = [((qst), i) for i in list]
                    x = np.array(inputs)
                    qst = x[0,0]
                    
                    #Launch the document classifier
                    tokenizer = settings.THETOKENIZER
                    encoded_data = tokenizer.batch_encode_plus(
                        zip(x[:,0],x[:,1]),
                        add_special_tokens=True,
                        return_attention_mask=True,
                        pad_to_max_length=True,
                        max_length=256,
                        return_tensors='pt'
                        )

                    input_ids = encoded_data['input_ids']
                    attention_masks = encoded_data['attention_mask']

                    dataset = TensorDataset(input_ids, attention_masks)

                    dataloader = DataLoader(dataset,
                                         sampler=SequentialSampler(dataset),
                                         batch_size=32)

                    modelClassifier = settings.MODELCLASSIFIER
                    device = settings.DEVICE
                    
                    def evaluate(dataloader_val):

                        modelClassifier.eval()
                        predictions, true_vals = [], []

                        for batch in dataloader_val:

                            batch = tuple(b.to(device) for b in batch)

                            inputs = {'input_ids':      batch[0],
                                   'attention_mask': batch[1],
                                  }

                            outputs = modelClassifier(**inputs)

                            logits = outputs[0]

                            logits = logits.detach().cpu().numpy()
                            predictions.append(logits)

                        predictions = np.concatenate(predictions, axis=0)

                        return predictions

                    predictions = evaluate(dataloader)
                    preds_flat = np.argmax(predictions, axis=1).flatten()
                    values = predictions[:,1]
                    answer = x[np.where(values == max(values)),1]
                    modelExtractor = settings.MODELEXTRACTOR
                    #Launch the answer extraction module
                    text = str(answer)
                    q = qst
                    encoding = tokenizer.encode_plus(q, text, max_length=256)
                    input_ids, token_type_ids = encoding["input_ids"], encoding["token_type_ids"]

                    start_scores, end_scores = modelExtractor(torch.tensor([input_ids]), token_type_ids=torch.tensor([token_type_ids]))
                    all_tokens = tokenizer.convert_ids_to_tokens(input_ids)

                    a = ' '.join(all_tokens[torch.argmax(start_scores) : torch.argmax(end_scores)+1])
                    answer_cleaned = a.replace(" ##", "")
                    answer_cleaned = answer_cleaned.replace('\\', "")
                    answer={'answer':answer_cleaned}


                # send to client side.
                return JsonResponse({"instance": answer}, status=200)
            else:
                return JsonResponse({"error": form.errors}, status=400)
    return JsonResponse({"error":""},status=400)
