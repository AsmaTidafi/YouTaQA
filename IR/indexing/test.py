import lucene
import wiki_extractor
from org.apache.lucene.search.similarities import *
from search import Searcher
from similarity import Similarity

inputQuery = ""
Similarity = Similarity()

while inputQuery != "exit":
    inputQuery = input("Enter your request, otherwise tape 'exit' to exit\n")
    if inputQuery == "exit":
        break

    searchObject = Searcher("/Users/younesagabi/Desktop/YouTaQA/IR/index_wiki_v7.0")
    result = searchObject.multiFieldsSearch(inputQuery, BM25Similarity())
    print(result)
    print("#" * 100)
    print("#" * 100)
    content = ""
    tab=['']
    j=0
    for i in range(len(result)):
        hitDoc = searchObject.searcher.doc(result[i].doc)
        score = result[i].score
        content = hitDoc.get("content_section")
        tab.append(content)
        print("#"*100)
        id = hitDoc.get("id_section")
        #print(id)
        #print(tab[j])
        #print("#"*100)
        #print("#"*100)
    tab.pop(0)   
    print(tab)    
    searchObject.reader.close()
    searchObject.directory.close()









