"""
RAG v3-improved 简化启动脚本
直接运行,无需复杂的模块导入
"""
import os
import sys

# 添加必要的路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

# 现在可以正常导入
from rag_agent_v3_improved import RAGAgentV3Improved


def main():
    """主函数"""
    try:
        agent = RAGAgentV3Improved()
        
        print("\n欢迎使用 RAG v3-improved 多模态智能体!")
        print("=" * 60)
        print("命令:")
        print("  - 直接输入问题进行对话")
        print("  - /rag on/off        开启/关闭 RAG 模式")
        print("  - /build <file>      增量更新特定文件")
        print("  - /sync [force]      同步新文档 (加 force 强制重跑所有)")
        print("  - /rebuild           重建知识库(提取图片和公式)")
        print("  - /search <query>    搜索知识库")
        print("  - /stats             显示索引统计")
        print("  - /quit              退出程序")
        print("=" * 60 + "\n")
        
        use_rag = True
        
        while True:
            try:
                user_input = input("您: ").strip()
                
                if not user_input:
                    continue
                
                # 处理命令
                if user_input.startswith('/'):
                    cmd = user_input.lower()
                    
                    if cmd == '/quit':
                        print("\n再见!")
                        break
                    
                    elif cmd == '/rag on':
                        use_rag = True
                        print("✓ RAG 模式已开启")
                        continue
                    
                    elif cmd == '/rag off':
                        use_rag = False
                        print("✓ RAG 模式已关闭")
                        continue
                    
                    elif cmd.startswith('/build '):
                         filename = cmd[7:].strip()
                         if not filename:
                             print("错误: 请指定文件名 (例如 /build LDO.pdf)")
                             continue
                         
                         print(f"\n开始增量更新: {filename}...")
                         ok = agent.rebuild_knowledge_base(target_filename=filename)
                         if ok:
                             print(f"\n✓ 文件 {filename} 更新完成")
                         else:
                             print(f"\n✗ 文件 {filename} 更新失败")
                         continue
                    
                    elif cmd.startswith('/sync'):
                         args = cmd.split()
                         force = False
                         if len(args) > 1 and args[1] == 'force':
                             force = True
                         
                         agent.sync_knowledge_base(force=force)
                         continue

                    elif cmd == '/rebuild':
                        print("\n开始重建知识库...")
                        ok = agent.rebuild_knowledge_base()
                        if ok:
                            print("\n✓ 知识库重建完成")
                        else:
                            print("\n✗ 知识库重建失败")
                        continue
                    
                    elif cmd.startswith('/search '):
                        query = user_input[8:].strip()
                        if query:
                            print(f"\n搜索: {query}")
                            docs, figs, eqs = agent.search_knowledge_base(query, k=5)
                            
                            print(f"\n找到:")
                            print(f"  - 文本块: {len(docs)} 个")
                            print(f"  - 图片: {len(figs)} 个")
                            print(f"  - 公式: {len(eqs)} 个")
                            
                            if docs:
                                print("\n文本块:")
                                for i, doc in enumerate(docs[:3], 1):
                                    print(f"  [{i}] {doc.page_content[:100]}...")
                            
                            if figs:
                                print("\n图片:")
                                for i, fig in enumerate(figs[:3], 1):
                                    print(f"  [{i}] {fig.get('caption', fig['figure_id'])}")
                            
                            if eqs:
                                print("\n公式:")
                                for i, eq in enumerate(eqs[:3], 1):
                                    print(f"  [{i}] {eq.get('text', eq['formula_id'])[:80]}")
                        continue
                    
                    elif cmd == '/stats':
                        agent.multimodal_index.print_statistics()
                        continue
                    
                    else:
                        print("未知命令")
                        continue
                
                # 进行对话
                print(f"\n智能体 v3-improved [RAG: {'ON' if use_rag else 'OFF'}]:")
                response = agent.chat(user_input, use_rag=use_rag)
                print(response)
                print()
                
            except KeyboardInterrupt:
                print("\n\n再见!")
                break
            except Exception as e:
                print(f"\n错误: {e}")
                import traceback
                traceback.print_exc()
    
    except Exception as e:
        print(f"\n初始化失败: {e}")
        print("\n请检查:")
        print("  1. .env 文件是否存在并配置了API密钥")
        print("  2. documents 目录是否存在")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
