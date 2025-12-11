
import json

def lookup():
    path = "d:/python/RAG/rag_test_v3/data_base_v3/multimodal_index.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        figs = data.get("figures", {})
        # Look for Any-Cap and p27
        targets = [k for k in figs.keys() if "Any-Cap" in k and "_p27_" in k]
        
        if not targets:
            print("No figures found for Any-Cap on page 27.")
        
        for k in targets:
            cap = figs[k].get("caption", "No Caption")
            print(f"File: {k}.png")
            print(f"Caption: {cap}")
            print("-" * 20)
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    lookup()
