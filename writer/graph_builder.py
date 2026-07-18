import json
import html as html_module


def build_graph_html(repository) -> str:
    """
    Build a self-contained, highly interactive HTML knowledge graph visualizer
    using Vis.js (Vis-Network) and clean CSS variables.
    Dynamically assigns colors to all categories found in the bundle.
    """

    # Prepare node data
    nodes_data = []
    edges_data = []

    for f in repository.files:
        # Determine category group
        parts = f.path.split("/")
        category = parts[0] if len(parts) > 1 else "general"

        nodes_data.append({
            "id": f.path,
            "label": f.title,
            "group": category,
            "title": html_module.escape(f.title),
            "type": html_module.escape(f.type),
            "description": html_module.escape(f.description),
            "tags": [html_module.escape(t) for t in f.tags],
            "pages": html_module.escape(
                f.metadata.get("source", {}).get("pages", "N/A")
            )
        })

        # Add links
        for rel in f.relationships:
            target_path = rel.get("target_path")
            if target_path:
                edges_data.append({
                    "from": f.path,
                    "to": target_path,
                    "label": rel.get("type", "related"),
                    "arrows": "to"
                })

    nodes_json = json.dumps(nodes_data, indent=2)
    edges_json = json.dumps(edges_data, indent=2)

    # Escape the repository title for safe HTML insertion
    safe_title = html_module.escape(repository.title)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title} — Knowledge Graph</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        :root {{
            --bg-color: #0b0f19;
            --panel-bg: #111827;
            --border-color: #1f2937;
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --accent-color: #3b82f6;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            height: 100vh;
            overflow: hidden;
            display: flex;
        }}

        #network-container {{
            flex: 1;
            height: 100%;
            position: relative;
        }}

        #network {{
            width: 100%;
            height: 100%;
        }}

        #sidebar {{
            width: 380px;
            background-color: var(--panel-bg);
            border-left: 1px solid var(--border-color);
            height: 100%;
            z-index: 10;
            box-shadow: -4px 0 20px rgba(0, 0, 0, 0.4);
            display: flex;
            flex-direction: column;
        }}

        .search-box {{
            padding: 20px;
            border-bottom: 1px solid var(--border-color);
        }}

        .search-input {{
            width: 100%;
            padding: 10px 14px;
            background-color: #1f2937;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-color);
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }}

        .search-input:focus {{
            border-color: var(--accent-color);
        }}

        .details-panel {{
            padding: 24px;
            flex: 1;
            overflow-y: auto;
        }}

        .welcome-msg {{
            color: var(--text-muted);
            text-align: center;
            margin-top: 100px;
            font-size: 14px;
            line-height: 1.6;
        }}

        .concept-title {{
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 8px;
            color: #fff;
        }}

        .concept-meta {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--accent-color);
        }}

        .info-label {{
            font-size: 11px;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 0.5px;
            margin-top: 20px;
            margin-bottom: 4px;
            font-weight: 600;
        }}

        .info-value {{
            font-size: 14px;
            line-height: 1.5;
        }}

        .tag-pill {{
            display: inline-block;
            background-color: #1f2937;
            color: var(--text-muted);
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 9999px;
            margin-right: 6px;
            margin-bottom: 6px;
            border: 1px solid var(--border-color);
        }}

        .legend {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background-color: rgba(17, 24, 39, 0.95);
            border: 1px solid var(--border-color);
            padding: 14px;
            border-radius: 12px;
            z-index: 5;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        }}

        .legend-title {{
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            font-size: 12px;
            margin-bottom: 6px;
        }}

        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 3px;
            margin-right: 8px;
        }}

        .stats-bar {{
            padding: 12px 20px;
            border-top: 1px solid var(--border-color);
            font-size: 12px;
            color: var(--text-muted);
            display: flex;
            gap: 16px;
        }}

        .stats-bar span {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
    </style>
</head>
<body>

    <div id="network-container">
        <div id="network"></div>
        
        <div class="legend">
            <div class="legend-title">Categories</div>
            <div id="legend-items"></div>
        </div>
    </div>

    <div id="sidebar">
        <div class="search-box">
            <input type="text" id="search" class="search-input" placeholder="Search concepts or tags...">
        </div>
        <div class="details-panel" id="details">
            <div class="welcome-msg">
                <h3>{safe_title}</h3>
                <p style="margin-top: 10px;">Click any concept node in the network to view its structured detail panel and relationships.</p>
            </div>
        </div>
        <div class="stats-bar">
            <span id="stats-nodes"></span>
            <span id="stats-edges"></span>
            <span id="stats-groups"></span>
        </div>
    </div>

    <script>
        const nodesData = {nodes_json};
        const edgesData = {edges_json};

        // Dynamic color palette — automatically assigns colors to all categories
        const COLOR_PALETTE = [
            "#ef4444", "#3b82f6", "#10b981", "#8b5cf6", "#f59e0b",
            "#ec4899", "#14b8a6", "#f97316", "#06b6d4", "#a855f7",
            "#84cc16", "#e11d48", "#0ea5e9", "#d946ef", "#22d3ee"
        ];

        const uniqueGroups = [...new Set(nodesData.map(n => n.group))];
        const groupColors = {{}};
        uniqueGroups.forEach((group, index) => {{
            groupColors[group] = COLOR_PALETTE[index % COLOR_PALETTE.length];
        }});

        // Render Legend
        const legendContainer = document.getElementById('legend-items');
        uniqueGroups.forEach(group => {{
            const color = groupColors[group];
            const item = document.createElement('div');
            item.className = 'legend-item';
            const label = group.replace(/-/g, ' ').toUpperCase();
            item.innerHTML = `
                <div class="legend-color" style="background-color: ${{color}}"></div>
                <span>${{label}}</span>
            `;
            legendContainer.appendChild(item);
        }});

        // Stats bar
        document.getElementById('stats-nodes').textContent = `${{nodesData.length}} concepts`;
        document.getElementById('stats-edges').textContent = `${{edgesData.length}} links`;
        document.getElementById('stats-groups').textContent = `${{uniqueGroups.length}} categories`;

        // Format nodes for Vis.js
        const visNodes = new vis.DataSet(nodesData.map(node => {{
            const color = groupColors[node.group] || '#6b7280';
            return {{
                id: node.id,
                label: node.label,
                color: {{
                    background: color,
                    border: color,
                    highlight: {{
                        background: color,
                        border: '#ffffff'
                    }}
                }},
                font: {{
                    color: '#ffffff',
                    size: 14
                }},
                borderWidth: 2,
                size: 25,
                shape: 'dot',
                shadow: {{
                    enabled: true,
                    color: 'rgba(0,0,0,0.5)',
                    size: 5
                }}
            }};
        }}));

        const visEdges = new vis.DataSet(edgesData.map(edge => {{
            return {{
                from: edge.from,
                to: edge.to,
                arrows: 'to',
                color: {{
                    color: '#4b5563',
                    highlight: '#3b82f6'
                }},
                width: 1.5,
                smooth: {{
                    type: 'cubicBezier',
                    forceDirection: 'none',
                    roundness: 0.5
                }}
            }};
        }}));

        const container = document.getElementById('network');
        const data = {{
            nodes: visNodes,
            edges: visEdges
        }};

        const options = {{
            physics: {{
                forceAtlas2Based: {{
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springLength: 100,
                    springConstant: 0.08
                }},
                solver: 'forceAtlas2Based',
                stabilization: {{
                    iterations: 150
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200
            }}
        }};

        const network = new vis.Network(container, data, options);

        // Sidebar detail view on click
        network.on("selectNode", function (params) {{
            const nodeId = params.nodes[0];
            const node = nodesData.find(n => n.id === nodeId);
            if (!node) return;

            const tagsHtml = node.tags.map(t => `<span class="tag-pill">${{t}}</span>`).join('') || '<span style="color:var(--text-muted);">None</span>';

            document.getElementById('details').innerHTML = `
                <div class="concept-title">${{node.title}}</div>
                <div class="concept-meta">${{node.type}}</div>
                
                <div class="info-label">Category Group</div>
                <div class="info-value">${{node.group.toUpperCase()}}</div>

                <div class="info-label">Source PDF Pages</div>
                <div class="info-value">Pages ${{node.pages}}</div>

                <div class="info-label">Description</div>
                <div class="info-value" style="color:#e5e7eb;">${{node.description}}</div>

                <div class="info-label">Tags</div>
                <div style="margin-top: 6px;">${{tagsHtml}}</div>

                <div class="info-label">Bundle Path</div>
                <div class="info-value" style="font-family: monospace; font-size: 12px; word-break: break-all; margin-top: 4px; padding: 6px; background:#1f2937; border-radius:4px; border:1px solid var(--border-color);">${{node.id}}</div>
            `;
        }});

        network.on("deselectNode", function () {{
            document.getElementById('details').innerHTML = `
                <div class="welcome-msg">
                    <h3>{safe_title}</h3>
                    <p style="margin-top: 10px;">Click any concept node in the network to view its structured detail panel and relationships.</p>
                </div>
            `;
        }});

        // Search feature
        document.getElementById('search').addEventListener('input', function (e) {{
            const query = e.target.value.toLowerCase().trim();
            if (!query) {{
                // Reset styling
                nodesData.forEach(n => {{
                    visNodes.update({{ id: n.id, opacity: 1.0 }});
                }});
                return;
            }}

            nodesData.forEach(n => {{
                const matches = n.title.toLowerCase().includes(query) || 
                                n.tags.some(t => t.toLowerCase().includes(query)) ||
                                n.description.toLowerCase().includes(query);
                visNodes.update({{
                    id: n.id,
                    opacity: matches ? 1.0 : 0.15
                }});
            }});
        }});
    </script>
</body>
</html>
"""
    return html
