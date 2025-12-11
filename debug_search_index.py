
import json
import os

def search_index():
    try:
        path = "d:/python/RAG/rag_test_v3/data_base_v3/multimodal_index.json"
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        figures = data.get('figures', {})
        print(f"Total figures in index: {len(figures)}")
        
        found = False
        for fig_id, info in figures.items():
            caption = info.get('caption', '')
            source = info.get('source', '')
            
            # Search for "Figure 24"
            if 'Figure 24' in caption or 'Fig. 24' in caption or 'Fig 24' in caption:
                print(f"MATCH: {fig_id}")
                print(f"  Source: {os.path.basename(source)}")
                print(f"  Caption: {caption}")
                found = True
                
        if not found:
            print("No figure with caption 'Figure 24' found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search_index()
