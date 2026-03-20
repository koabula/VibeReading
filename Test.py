from pathlib import Path

from NanoRAG import NanoRAG


WORKING_DIR = Path("./nano_graphrag_cache_qwen_test")
INPUT_FILE = Path("./Part1.md")
QUERY = "这份材料的主要内容是什么?"


def main() -> None:
    rag = NanoRAG(working_dir=WORKING_DIR, env_file=".env")

    status = rag.index_file(
        INPUT_FILE,
        reuse_existing=True,
        incremental=True,
        incremental_parts=2,
    )
    print(f"Index status: {status}")

    print("\nLocal query result:\n")
    print(rag.query(QUERY, mode="local"))

    html_path = rag.export_interactive_graph()
    print(f"\nInteractive graph exported: {html_path}")


if __name__ == "__main__":
    main()
