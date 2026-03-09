import json
import os
import platform
from pathlib import Path

if platform.system() == "Windows":
    raise RuntimeError(
        "CodeGraphContext uses redislite/FalkorDB, which does not support Windows.\n"
        "Please run the project using WSL or Docker."
    )

from redislite import FalkorDB


def generate_visualization():
    db_path = os.path.expanduser("~/.codegraphcontext/falkordb.db")
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    print(f"Reading graph from {db_path}...")
    f = FalkorDB(db_path)
    g = f.select_graph("codegraph")

    # Fetch nodes
    nodes_res = g.query("MATCH (n) RETURN id(n), labels(n)[0], n.name, n.path")
    nodes = []
    for row in nodes_res.result_set:
        node_id, label, name, path = row
        # Format label and name for display
        display_name = name if name else (os.path.basename(path) if path else label)
        nodes.append(
            {
                "id": node_id,
                "label": display_name,
                "group": label,
                "title": f"Type: {label}\nPath: {path}",
            }
        )

    # Fetch relationships
    edges_res = g.query("MATCH (s)-[r]->(t) RETURN id(s), type(r), id(t)")
    edges = []
    for row in edges_res.result_set:
        source, rel_type, target = row
        edges.append({"from": source, "to": target, "label": rel_type, "arrows": "to"})

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>CGC Graph Visualization</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        body {{
            margin: 0;
            padding: 0;
            background-color: #1a1a1a;
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            overflow: hidden;
        }}
        #mynetwork {{
            width: 100vw;
            height: 100vh;
        }}
        .header {{
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 10;
            background: rgba(0,0,0,0.7);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #444;
            pointer-events: none;
        }}
        h1 {{ margin: 0; font-size: 1.5em; color: #00d4ff; }}
        .stats {{ font-size: 0.9em; color: #aaa; margin-top: 5px; }}
        .controls {{
            position: absolute;
            top: 20px;
            right: 20px;
            z-index: 10;
            background: rgba(0,0,0,0.7);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #444;
        }}
        .controls label {{ display: block; margin-bottom: 8px; font-weight: 600; }}
        .controls input[type="range"] {{ width: 180px; cursor: pointer; }}
        .controls .value {{ display: inline-block; width: 40px; text-align: right; font-weight: 700; color: #00d4ff; }}
        .controls .hint {{ font-size: 0.75em; color: #888; margin-top: 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>CodeGraphContext Visualizer</h1>
        <div class="stats">Nodes: {len(nodes)} | Relationships: {len(edges)}</div>
        <div style="font-size: 0.8em; margin-top: 10px; color: #888;">Drag to move | Scroll to zoom</div>
    </div>
    <div class="controls">
        <label>Max Children: <span class="value" id="maxChildrenValue">10</span></label>
        <input type="range" id="maxChildrenSlider" min="1" max="50" value="10">
        <div class="hint">Click "+N more" to expand</div>
    </div>
    <div id="mynetwork"></div>

    <script type="text/javascript">
        const originalNodes = {json.dumps(nodes)};
        const originalEdges = {json.dumps(edges)};

        let maxChildren = 10;
        let nodes = new vis.DataSet();
        let edges = new vis.DataSet();

        function getRestNodeColor() {{
            return {{
                background: '#6B7280',
                border: '#4B5563'
            }};
        }}

        function truncateGraph() {{
            const childrenByParent = {{}};

            originalEdges.forEach(e => {{
                const from = String(e.from);
                if (!childrenByParent[from]) childrenByParent[from] = [];
                childrenByParent[from].push(e);
            }});

            const filteredNodes = [];
            const filteredEdges = [];
            const addedNodes = new Set();

            originalNodes.forEach(n => {{
                const id = String(n.id);
                filteredNodes.push({{
                    id: id,
                    label: n.label,
                    group: n.group,
                    title: n.title
                }});
                addedNodes.add(id);
            }});

            Object.entries(childrenByParent).forEach(([parentId, childEdges]) => {{
                const parent = String(parentId);
                const total = childEdges.length;

                if (total > maxChildren) {{
                    const shown = childEdges.slice(0, maxChildren);
                    const remaining = total - maxChildren;

                    shown.forEach(e => {{
                        filteredEdges.push({{
                            from: String(e.from),
                            to: String(e.to),
                            label: e.label,
                            arrows: e.arrows || 'to'
                        }});
                    }});

                    const restId = 'rest_' + parent;
                    if (!addedNodes.has(restId)) {{
                        filteredNodes.push({{
                            id: restId,
                            label: '+' + remaining + ' more',
                            group: 'Rest',
                            shape: 'diamond',
                            color: getRestNodeColor(),
                            font: {{ color: '#ffffff', size: 12 }}
                        }});
                        addedNodes.add(restId);
                    }}

                    filteredEdges.push({{
                        from: parent,
                        to: restId,
                        label: 'more',
                        arrows: 'to',
                        color: {{ color: '#6B7280' }},
                        dashes: true
                    }});
                }} else {{
                    childEdges.forEach(e => {{
                        filteredEdges.push({{
                            from: String(e.from),
                            to: String(e.to),
                            label: e.label,
                            arrows: e.arrows || 'to'
                        }});
                    }});
                }}
            }});

            nodes.clear();
            nodes.add(filteredNodes);
            edges.clear();
            edges.add(filteredEdges);

            if (window.network) {{
                window.network.fit();
            }}
        }}

        var container = document.getElementById('mynetwork');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var options = {{
            nodes: {{
                shape: 'dot',
                size: 16,
                font: {{ color: '#ffffff', size: 12 }},
                borderWidth: 2,
                shadow: true
            }},
            edges: {{
                width: 2,
                color: {{ color: '#666666', highlight: '#00d4ff' }},
                font: {{ size: 10, align: 'middle', color: '#aaaaaa' }},
                smooth: {{ type: 'continuous' }}
            }},
            groups: {{
                Repository: {{ color: {{ background: '#e91e63', border: '#c2185b' }} }},
                File: {{ color: {{ background: '#2196f3', border: '#1976d2' }} }},
                Function: {{ color: {{ background: '#4caf50', border: '#388e3c' }} }},
                Class: {{ color: {{ background: '#ff9800', border: '#f57c00' }} }},
                Module: {{ color: {{ background: '#9c27b0', border: '#7b1fa2' }} }},
                Variable: {{ color: {{ background: '#607d8b', border: '#455a64' }} }}
            }},
            physics: {{
                forceAtlas2Based: {{
                    gravitationalConstant: -26,
                    centralGravity: 0.005,
                    springLength: 230,
                    springConstant: 0.18
                }},
                maxVelocity: 146,
                solver: 'forceAtlas2Based',
                timestep: 0.35,
                stabilization: {{ iterations: 150 }}
            }}
        }};
        window.network = new vis.Network(container, data, options);

        truncateGraph();

        document.getElementById('maxChildrenSlider').addEventListener('input', function(e) {{
            maxChildren = parseInt(e.target.value);
            document.getElementById('maxChildrenValue').textContent = maxChildren;
            truncateGraph();
        }});

        window.network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                if (String(nodeId).startsWith('rest_')) {{
                    maxChildren += 10;
                    document.getElementById('maxChildrenSlider').value = maxChildren;
                    document.getElementById('maxChildrenValue').textContent = maxChildren;
                    truncateGraph();
                }}
            }}
        }});
    </script>
</body>
</html>
    """

    target_path = Path.cwd() / "graph_viz.html"
    with open(target_path, "w") as f:
        f.write(html_content)

    print(f"\n✅ Visualization generated successfully!")
    print(f"👉 Open this file in your browser: file://{target_path.absolute()}")


if __name__ == "__main__":
    generate_visualization()
