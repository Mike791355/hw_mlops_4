"""Скриншоты документации и DAG."""
import argparse
import functools
import http.server
import json
import threading
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    directory = args.out.resolve()
    if not (directory / "static_index.html").is_file():
        raise FileNotFoundError("Run the dbt pipeline (docs generate --static) first")
    manifest = json.loads((directory / "manifest.json").read_text())
    expected_nodes = [
        uid for uid, node in manifest["nodes"].items()
        if node["resource_type"] == "model" and node["package_name"] == "fraud_analytics"
    ] + list(manifest["sources"])
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory)),
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1600, "height": 1050}, device_scale_factor=1)
            base = f"http://127.0.0.1:{server.server_port}/static_index.html"
            page.goto(base + "#!/model/model.fraud_analytics.stg_transactions", wait_until="networkidle")
            page.locator("h1").filter(has_text="stg_transactions").wait_for(timeout=60000)
            page.screenshot(path=str(directory / "dbt-docs.png"), full_page=True)
            # Граф dbt Docs рисуется на canvas.
            graph_page = browser.new_page(viewport={"width": 1800, "height": 1100}, device_scale_factor=1)
            query = urlencode({"g_v": 1, "g_i": "+stg_transactions+"})
            graph_page.goto(base + "#!/overview?" + query, wait_until="networkidle")
            graph_page.locator("#cy canvas").first.wait_for(state="visible", timeout=60000)
            graph_page.wait_for_function(
                """ids => {
                    const cy = document.getElementById('cy')?._cyreg?.cy;
                    return cy && typeof cy.nodes === 'function'
                        && ids.every(id => cy.$id(id).length === 1)
                        && new Set(cy.nodes().map(n => n.position('x'))).size > 1;
                }""",
                arg=expected_nodes,
                timeout=60000,
            )
            graph_page.evaluate("""() => {
                const cy = document.getElementById('cy')._cyreg.cy;
                cy.resize();
                cy.fit(cy.elements(), 60);
                return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            }""")
            graph_page.screenshot(path=str(directory / "dbt-dag.png"), animations="disabled")
            graph_nodes = graph_page.evaluate("""() => {
                const cy = document.getElementById('cy')._cyreg.cy;
                return {
                    nodes: cy.nodes().map(n => ({id: n.id(), label: n.data('label')})),
                    edges: cy.edges().map(e => ({source: e.source().id(), target: e.target().id()}))
                };
            }""")
            (directory / "dbt-dag-nodes.json").write_text(json.dumps(graph_nodes, indent=2) + "\n")
            (directory / "screenshots_status.json").write_text(json.dumps({
                "success": True,
                "docs": "dbt-docs.png",
                "dag": "dbt-dag.png",
                "verified_nodes": expected_nodes,
            }, indent=2) + "\n")
            browser.close()
    finally:
        server.shutdown()
    print(f"Saved dbt-docs.png and dbt-dag.png in {directory}")


if __name__ == "__main__":
    main()
