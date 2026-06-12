/* ============================================================
   Research Cartographer — D3.js Force-Directed Graph + WebSocket
   ============================================================ */

(() => {
    "use strict";

    // ─── Configuration ───
    const CONFIG = {
        api: {
            base: window.location.origin || "http://localhost:8000",
            ws: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host || "localhost:8000"}/ws/graph`,
            graphEndpoint: "/graph",
            uploadEndpoint: "/upload",
        },
        ws: {
            reconnectDelay: 2000,
            maxReconnectDelay: 30000,
            reconnectBackoff: 1.5,
        },
        graph: {
            // Force simulation
            chargeStrength: -500,
            linkDistance: 310,
            centerStrength: 0.015,
            collisionRadius: 35,
            alphaDecay: 0.04,
            velocityDecay: 0.35,

            // Node sizing
            minNodeRadius: 6,
            maxNodeRadius: 28,
            labelOffset: 6,

            // Edge sizing
            minEdgeWidth: 1,
            maxEdgeWidth: 6,
        },
        colors: {
            paper: "#4a9eff",
            finding: "#00ff88",
            method: "#ffd700",
            assumption: "#ffd700",
            limitation: "#ff8c42",
            contradiction: "#EF4444", // red-500
            concept: "#8B5CF6",    // violet-500
            question: "#F3F4F6",   // gray-100
            // Edges
            supports: "#10B981",
            contradicts: "#ff4444",
            extends: "#4a9eff",
            replicates: "#6b7280",
            refines: "#6b7280",
        },
    };

    // ─── State ───
    const state = {
        nodes: new Map(),       // id → node data
        edges: new Map(),       // id → edge data
        simulation: null,
        svg: null,
        g: null,                // main group (zoom/pan target)
        edgeGroup: null,
        nodeGroup: null,
        zoom: null,
        ws: null,
        wsReconnectTimer: null,
        wsReconnectDelay: CONFIG.ws.reconnectDelay,
        selectedNodeId: null,
        tooltip: null,
        traceStartNodeId: null,   // id of first node selected for tracing
        tracePath: null,           // { nodeIds: Set<string>, edgeIds: Set<string> } | null
    };

    // ─── DOM Refs ───
    const dom = {};

    // ─── Initialize ───
    function init() {
        cacheDom();
        createTooltip();
        initSvg();
        initSimulation();
        initZoom();
        bindUpload();
        bindPanelClose();
        bindZoomControls();

        // Fetch initial graph then connect WS
        fetchInitialGraph().then(() => {
            connectWebSocket();
        });
        
        initSearch();
        initReview();
    }

    function cacheDom() {
        dom.svg = document.getElementById("graph-svg");
        dom.emptyState = document.getElementById("empty-state");
        dom.pipelineStatus = document.getElementById("pipeline-status");
        dom.wsIndicator = document.getElementById("ws-indicator");
        dom.wsLabel = dom.wsIndicator.querySelector(".ws-label");
        dom.statusDot = dom.pipelineStatus.querySelector(".status-dot");
        dom.statusLabel = dom.pipelineStatus.querySelector(".status-label");
        dom.detailPanel = document.getElementById("detail-panel");
        dom.panelTitle = document.getElementById("panel-title");
        dom.panelBody = document.getElementById("panel-body");
        dom.panelClose = document.getElementById("panel-close");
        dom.uploadDropzone = document.getElementById("upload-dropzone");
        dom.fileInput = document.getElementById("file-input");
        dom.uploadProgress = document.getElementById("upload-progress");
        dom.progressFill = document.getElementById("progress-fill");
        dom.uploadStatusText = document.getElementById("upload-status-text");
        dom.uploadContent = dom.uploadDropzone.querySelector(".upload-content");
        dom.toastContainer = document.getElementById("toast-container");
        // Stats
        dom.statPapers = document.getElementById("stat-papers");
        dom.statClaims = document.getElementById("stat-claims");
        dom.statEdges = document.getElementById("stat-edges");
        dom.statQuestions = document.getElementById("stat-questions");
        dom.searchBtn = document.getElementById("search-btn");
        dom.searchOverlay = document.getElementById("search-overlay");
        dom.searchInput = document.getElementById("search-input");

        // Review (populated in FEATURE_literature_review)
        dom.reviewBtn = document.getElementById("review-btn");
        dom.reviewModal = document.getElementById("review-modal");
        dom.reviewContent = document.getElementById("review-content");
        dom.reviewDownloadBtn = document.getElementById("review-download-btn");
        dom.reviewCloseBtn = document.getElementById("review-close-btn");
    }

    // ─── Tooltip ───
    function createTooltip() {
        state.tooltip = document.createElement("div");
        state.tooltip.className = "graph-tooltip";
        document.body.appendChild(state.tooltip);
    }

    function showTooltip(text, x, y) {
        state.tooltip.textContent = text;
        state.tooltip.style.left = `${x + 14}px`;
        state.tooltip.style.top = `${y - 10}px`;
        state.tooltip.classList.add("visible");
    }

    function hideTooltip() {
        state.tooltip.classList.remove("visible");
    }

    // ─── SVG Setup ───
    function initSvg() {
        const svg = d3.select(dom.svg);
        state.svg = svg;

        // Defs for glow filters and arrowheads
        const defs = svg.append("defs");

        // Glow filter for nodes
        const glowFilter = defs.append("filter")
            .attr("id", "node-glow")
            .attr("x", "-50%").attr("y", "-50%")
            .attr("width", "200%").attr("height", "200%");
        glowFilter.append("feGaussianBlur")
            .attr("stdDeviation", "4")
            .attr("result", "coloredBlur");
        const feMerge = glowFilter.append("feMerge");
        feMerge.append("feMergeNode").attr("in", "coloredBlur");
        feMerge.append("feMergeNode").attr("in", "SourceGraphic");

        // Strong glow for questions
        const strongGlow = defs.append("filter")
            .attr("id", "question-glow")
            .attr("x", "-80%").attr("y", "-80%")
            .attr("width", "260%").attr("height", "260%");
        strongGlow.append("feGaussianBlur")
            .attr("stdDeviation", "8")
            .attr("result", "coloredBlur");
        const feMerge2 = strongGlow.append("feMerge");
        feMerge2.append("feMergeNode").attr("in", "coloredBlur");
        feMerge2.append("feMergeNode").attr("in", "SourceGraphic");

        // Contradiction pulse filter
        const pulseGlow = defs.append("filter")
            .attr("id", "contradiction-glow")
            .attr("x", "-100%").attr("y", "-100%")
            .attr("width", "300%").attr("height", "300%");
        pulseGlow.append("feGaussianBlur")
            .attr("stdDeviation", "6")
            .attr("result", "coloredBlur");
        const feMerge3 = pulseGlow.append("feMerge");
        feMerge3.append("feMergeNode").attr("in", "coloredBlur");
        feMerge3.append("feMergeNode").attr("in", "SourceGraphic");

        // Arrow markers for each edge type
        const arrowTypes = [
            { id: "arrow-supports", color: CONFIG.colors.supports },
            { id: "arrow-contradicts", color: CONFIG.colors.contradicts },
            { id: "arrow-extends", color: CONFIG.colors.extends },
            { id: "arrow-replicates", color: CONFIG.colors.replicates },
            { id: "arrow-refines", color: CONFIG.colors.refines },
        ];

        arrowTypes.forEach(({ id, color }) => {
            defs.append("marker")
                .attr("id", id)
                .attr("viewBox", "0 -5 10 10")
                .attr("refX", 20)
                .attr("refY", 0)
                .attr("markerWidth", 6)
                .attr("markerHeight", 6)
                .attr("orient", "auto")
                .append("path")
                .attr("d", "M0,-4L10,0L0,4")
                .attr("fill", color)
                .attr("opacity", 0.6);
        });

        // Main group for zoom/pan
        state.g = svg.append("g").attr("class", "graph-root");
        state.edgeGroup = state.g.append("g").attr("class", "edges-layer");
        state.nodeGroup = state.g.append("g").attr("class", "nodes-layer");
    }

    // ─── Force Simulation ───
    function initSimulation() {
        const width = dom.svg.clientWidth;
        const height = dom.svg.clientHeight;

        state.simulation = d3.forceSimulation()
            .force("link", d3.forceLink()
                .id(d => d.id)
                .distance(CONFIG.graph.linkDistance)
            )
            .force("charge", d3.forceManyBody()
                .strength(CONFIG.graph.chargeStrength)
            )
            .force("center", d3.forceCenter(width / 2, height / 2)
                .strength(CONFIG.graph.centerStrength)
            )
            .force("collision", d3.forceCollide()
                .radius(d => nodeRadius(d) + 4)
            )
            .alphaDecay(CONFIG.graph.alphaDecay)
            .velocityDecay(CONFIG.graph.velocityDecay)
            .on("tick", ticked);
    }

    // ─── Zoom / Pan ───
    function initZoom() {
        state.zoom = d3.zoom()
            .scaleExtent([0.1, 6])
            .on("zoom", (event) => {
                state.g.attr("transform", event.transform);
            });

        state.svg.call(state.zoom);
    }

    function bindZoomControls() {
        document.getElementById("zoom-in").addEventListener("click", () => {
            state.svg.transition().duration(300).call(state.zoom.scaleBy, 1.4);
        });
        document.getElementById("zoom-out").addEventListener("click", () => {
            state.svg.transition().duration(300).call(state.zoom.scaleBy, 0.7);
        });
        document.getElementById("zoom-reset").addEventListener("click", () => {
            state.svg.transition().duration(500).call(
                state.zoom.transform,
                d3.zoomIdentity.translate(dom.svg.clientWidth / 2, dom.svg.clientHeight / 2).scale(0.8).translate(-dom.svg.clientWidth / 2, -dom.svg.clientHeight / 2)
            );
        });
    }

    // ─── Node Helpers ───
    function getNodeColor(node) {
        if (node.label === "OpenQuestion") return CONFIG.colors.question;
        if (node.label === "Paper") return CONFIG.colors.paper;
        if (node.label === "Concept") return CONFIG.colors.concept;
        if (node.label === "Claim") {
            // Check for contradiction involvement
            if (node._hasContradiction) return CONFIG.colors.contradiction;
            const type = (node.type || "finding").toLowerCase();
            if (type === "finding" || type === "result") return CONFIG.colors.finding;
            if (type === "method") return CONFIG.colors.method;
            if (type === "assumption") return CONFIG.colors.assumption;
            if (type === "limitation") return CONFIG.colors.limitation;
            return CONFIG.colors.finding;
        }
        return CONFIG.colors.paper;
    }

    function nodeRadius(node) {
        const conns = node._connectionCount || 1;
        const r = CONFIG.graph.minNodeRadius + Math.sqrt(conns) * 3.5;
        return Math.min(r, CONFIG.graph.maxNodeRadius);
    }

    function getNodeLabel(node) {
        if (node.label === "Paper") return node.title ? truncate(node.title, 24) : "Paper";
        if (node.label === "Claim") return truncate(node.text || "Claim", 20);
        if (node.label === "Concept") return node.name || "Concept";
        if (node.label === "OpenQuestion") return truncate(node.question || "Question", 20);
        return node.id.slice(0, 8);
    }

    function truncate(str, len) {
        if (!str) return "";
        return str.length > len ? str.slice(0, len) + "…" : str;
    }

    // ─── Edge Helpers ───
    function getEdgeColor(edge) {
        const type = (edge.type || "supports").toLowerCase();
        return CONFIG.colors[type] || CONFIG.colors.replicates;
    }

    function getEdgeClass(edge) {
        return (edge.type || "supports").toLowerCase();
    }

    function edgeWidth(edge) {
        const s = edge.strength || 0.5;
        return CONFIG.graph.minEdgeWidth + s * (CONFIG.graph.maxEdgeWidth - CONFIG.graph.minEdgeWidth);
    }

    // ─── Compute Derived Fields ───
    function recomputeDerivedFields() {
        // Reset connection counts
        state.nodes.forEach(n => {
            n._connectionCount = 0;
            n._hasContradiction = false;
        });

        state.edges.forEach(e => {
            const src = state.nodes.get(e.source_claim_id || e.source?.id || e.source);
            const tgt = state.nodes.get(e.target_claim_id || e.target?.id || e.target);
            if (src) src._connectionCount = (src._connectionCount || 0) + 1;
            if (tgt) tgt._connectionCount = (tgt._connectionCount || 0) + 1;
            if (e.type === "contradicts") {
                if (src) src._hasContradiction = true;
                if (tgt) tgt._hasContradiction = true;
            }
        });
    }

    let renderTimeout = null;
    // ─── Render Graph ───
    function render(animate = false) {
        if (renderTimeout) clearTimeout(renderTimeout);
        renderTimeout = setTimeout(() => {
            recomputeDerivedFields();
            updateEmptyState();
            updateStats();

            const nodesArr = Array.from(state.nodes.values());
        const edgesArr = Array.from(state.edges.values()).map(e => ({
            ...e,
            source: e.source_claim_id || e.source,
            target: e.target_claim_id || e.target,
        })).filter(e => state.nodes.has(typeof e.source === 'object' ? e.source.id : e.source) &&
                         state.nodes.has(typeof e.target === 'object' ? e.target.id : e.target));

        // ── Edges ──
        const edgeSel = state.edgeGroup
            .selectAll(".edge-container")
            .data(edgesArr, d => d.id);

        edgeSel.exit().transition().duration(300).style("opacity", 0).remove();

        const edgeEnter = edgeSel.enter()
            .append("g")
            .attr("class", "edge-container");

        edgeEnter
            .append("line")
            .attr("class", d => `edge-line ${getEdgeClass(d)}${animate ? " edge-enter" : ""}`)
            .attr("stroke", d => getEdgeColor(d))
            .attr("stroke-width", d => edgeWidth(d))
            .attr("stroke-opacity", 0.45)
            .attr("marker-end", d => `url(#arrow-${getEdgeClass(d)})`);

        edgeEnter
            .append("line")
            .attr("class", "edge-hitbox")
            .attr("stroke", "transparent")
            .attr("stroke-width", 24)
            .style("cursor", "pointer")
            .on("click", (event, d) => {
                event.stopPropagation();
                const relType = (d.rel_type || d.type || "").toUpperCase();
                if (relType === "CONTAINS" || relType === "RELATES_TO" || relType === "GAPS") return;
                openEdgeDetailPanel(d);
            })
            .on("mouseenter", function(event, d) {
                const parentNode = this.parentNode;
                d3.select(parentNode).select(".edge-line")
                    .transition().duration(150)
                    .attr("stroke-opacity", 0.85)
                    .attr("stroke-width", edgeWidth(d) * 1.8);
                const label = `${d.type || "edge"} (${Math.round((d.strength || 0) * 100)}%)`;
                showTooltip(label, event.clientX, event.clientY);
            })
            .on("mousemove", (event) => {
                state.tooltip.style.left = `${event.clientX + 14}px`;
                state.tooltip.style.top = `${event.clientY - 10}px`;
            })
            .on("mouseleave", function(event, d) {
                const parentNode = this.parentNode;
                d3.select(parentNode).select(".edge-line")
                    .transition().duration(150)
                    .attr("stroke-opacity", 0.45)
                    .attr("stroke-width", edgeWidth(d));
                hideTooltip();
            });

        const edgeMerge = edgeEnter.merge(edgeSel);

        edgeMerge.select(".edge-line")
            .attr("stroke", d => getEdgeColor(d))
            .attr("stroke-width", d => edgeWidth(d));

        // ── Nodes ──
        const nodeSel = state.nodeGroup
            .selectAll(".node-group")
            .data(nodesArr, d => d.id);

        nodeSel.exit().transition().duration(300).style("opacity", 0).remove();

        const nodeEnter = nodeSel.enter()
            .append("g")
            .attr("class", d => `node-group${animate ? " node-enter" : ""}`)
            .call(drag(state.simulation));

        // Outer glow circle
        nodeEnter.append("circle")
            .attr("class", d => {
                if (d.label === "OpenQuestion") return "node-glow question-glow";
                return "node-glow";
            })
            .attr("r", d => nodeRadius(d) + 8)
            .attr("fill", d => getNodeColor(d))
            .attr("opacity", d => d.label === "OpenQuestion" ? 0.25 : 0.15)
            .attr("filter", d => d.label === "OpenQuestion" ? "url(#question-glow)" : null);

        // Contradiction halo
        nodeEnter.append("circle")
            .attr("class", d => `contradiction-halo${d._hasContradiction ? " active" : ""}`)
            .attr("r", d => nodeRadius(d) + 14)
            .attr("stroke", CONFIG.colors.contradiction)
            .attr("stroke-width", 2)
            .attr("fill", "none")
            .attr("filter", "url(#contradiction-glow)");

        // Core circle
        nodeEnter.append("circle")
            .attr("class", "node-circle")
            .attr("r", d => nodeRadius(d))
            .attr("fill", d => getNodeColor(d))
            .attr("stroke", d => d.label === "Paper" ? "rgba(255,255,255,0.2)" : "none")
            .attr("stroke-width", 2);

        // Glow burst for new nodes
        if (animate) {
            nodeEnter.append("circle")
                .attr("class", "glow-burst")
                .attr("r", 5)
                .attr("fill", d => getNodeColor(d))
                .attr("opacity", 0.7);
        }

        // Label
        nodeEnter.append("text")
            .attr("class", "node-label")
            .attr("dy", d => nodeRadius(d) + CONFIG.graph.labelOffset + 12)
            .text(d => getNodeLabel(d));

        // Interactions
        nodeEnter
            .on("click", (event, d) => {
                event.stopPropagation();
                if (event.shiftKey) {
                    handleTraceClick(d);
                } else {
                    openDetailPanel(d);
                }
            })
            .on("mouseenter", (event, d) => {
                const label = d.label === "Claim" ? (d.text || "Claim")
                    : d.label === "Paper" ? (d.title || "Paper")
                    : d.label === "Concept" ? (d.name || "Concept")
                    : d.label === "OpenQuestion" ? (d.question || "Question")
                    : d.id;
                showTooltip(truncate(label, 80), event.clientX, event.clientY);
            })
            .on("mousemove", (event) => {
                state.tooltip.style.left = `${event.clientX + 14}px`;
                state.tooltip.style.top = `${event.clientY - 10}px`;
            })
            .on("mouseleave", () => hideTooltip());

        const nodeMerge = nodeEnter.merge(nodeSel);

        // Update existing nodes
        nodeMerge.select(".node-circle")
            .transition().duration(400)
            .attr("r", d => nodeRadius(d))
            .attr("fill", d => getNodeColor(d))
            .attr("stroke", d => d3.color(getNodeColor(d)).brighter(0.5));

        nodeMerge.select(".node-glow")
            .transition().duration(400)
            .attr("r", d => nodeRadius(d) + 8)
            .attr("fill", d => getNodeColor(d));

        nodeMerge.select(".contradiction-halo")
            .classed("active", d => d._hasContradiction)
            .transition().duration(400)
            .attr("r", d => nodeRadius(d) + 14);

        nodeMerge.select(".node-label")
            .text(d => getNodeLabel(d))
            .transition().duration(400)
            .attr("dy", d => nodeRadius(d) + CONFIG.graph.labelOffset + 12);

        // Update simulation
        state.simulation.nodes(nodesArr);
        state.simulation.force("link").links(edgesArr);
        state.simulation.alpha(0.3).restart();

        // ── Trace Highlighting ───────────────────────────────────────
        nodeMerge.classed("trace-start",
            d => state.traceStartNodeId === d.id);
        nodeMerge.classed("trace-path-node",
            d => !!(state.tracePath && state.tracePath.nodeIds.has(d.id)));
        state.edgeGroup.selectAll("line.edge-line")
            .classed("trace-path-edge",
                d => !!(state.tracePath && state.tracePath.edgeIds.has(d.id)));
        // ─────────────────────────────────────────────────────────────

        }, 50); // debounce delay
    }

    // ─── Tick ───
    function ticked() {
        state.edgeGroup.selectAll(".edge-line, .edge-hitbox")
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        state.nodeGroup.selectAll(".node-group")
            .attr("transform", d => `translate(${d.x},${d.y})`);
    }

    // ─── Drag ───
    function drag(simulation) {
        return d3.drag()
            .on("start", (event, d) => {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            })
            .on("drag", (event, d) => {
                d.fx = event.x;
                d.fy = event.y;
            })
            .on("end", (event, d) => {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            });
    }

    // ─── Empty State / Stats ───
    function updateEmptyState() {
        if (state.nodes.size > 0) {
            dom.emptyState.classList.add("hidden");
        } else {
            dom.emptyState.classList.remove("hidden");
        }
    }

    function updateStats() {
        let papers = 0, claims = 0, questions = 0, concepts = 0, limitations = 0;
        state.nodes.forEach(n => {
            if (n.label === "Paper") papers++;
            else if (n.label === "Claim") {
                claims++;
                if (n.type && n.type.toLowerCase() === "limitation") limitations++;
            }
            else if (n.label === "OpenQuestion") questions++;
            else if (n.label === "Concept") concepts++;
        });
        
        let contradictions = 0;
        state.edges.forEach(e => {
            const t = e.type || e.rel_type;
            if (t && t.toLowerCase() === "contradicts") {
                contradictions++;
            }
        });
        
        dom.statPapers.textContent = papers;
        dom.statClaims.textContent = claims;
        dom.statEdges.textContent = state.edges.size;
        dom.statQuestions.textContent = questions;
        if (!dom.statConcepts) dom.statConcepts = document.getElementById("stat-concepts");
        if (!dom.statContradictions) dom.statContradictions = document.getElementById("stat-contradictions");
        if (!dom.statLimitations) dom.statLimitations = document.getElementById("stat-limitations");
        if (dom.statConcepts) dom.statConcepts.textContent = concepts;
        if (dom.statContradictions) dom.statContradictions.textContent = contradictions;
        if (dom.statLimitations) dom.statLimitations.textContent = limitations;
    }

    // ─── Field Consensus Meter ───
    function computeConsensus(claimId) {
        // Reads state.edges to compute a weighted consensus score.
        // Returns null when no cross-paper semantic edges exist (single paper loaded).
        // CONTAINS and RELATES_TO edges are excluded — semantic only.

        const SEMANTIC_TYPES = new Set([
            "supports", "contradicts", "extends", "replicates", "refines"
        ]);
        const SUPPORT_WEIGHT = { supports: 1.0, replicates: 1.0, extends: 0.5, refines: 0.5 };

        let supportScore = 0, disputeScore = 0;
        let supportCount = 0, disputeCount = 0, extendCount = 0;

        state.edges.forEach(e => {
            const srcId = typeof e.source === "object" ? e.source.id : (e.source_claim_id || e.source);
            const tgtId = typeof e.target === "object" ? e.target.id : (e.target_claim_id || e.target);
            if (srcId !== claimId && tgtId !== claimId) return;

            const type = (e.type || e.rel_type || "").toLowerCase();
            if (!SEMANTIC_TYPES.has(type)) return;

            const strength = typeof e.strength === "number" ? e.strength : 0.5;

            if (type === "contradicts") {
                disputeScore += strength;
                disputeCount++;
            } else if (type === "extends" || type === "refines") {
                supportScore += strength * (SUPPORT_WEIGHT[type] || 0.5);
                extendCount++;
            } else {
                supportScore += strength * (SUPPORT_WEIGHT[type] || 1.0);
                supportCount++;
            }
        });

        const totalScore = supportScore + disputeScore;
        if (totalScore === 0) return null;

        return {
            consensusPct: Math.round((supportScore / totalScore) * 100),
            supportCount,
            disputeCount,
            extendCount,
            totalEdges: supportCount + disputeCount + extendCount,
        };
    }

    // ─── Detail Panel ───
// ─── Search / Claim Verification ─────────────────────────────────────────

    function initSearch() {
        // Press "/" to open (only when focus is on body, not an input)
        document.addEventListener("keydown", e => {
            if (e.key === "/" && e.target === document.body) {
                e.preventDefault();
                openSearchOverlay();
            }
            if (e.key === "Escape") {
                closeSearchOverlay();
                if (state.traceStartNodeId || state.tracePath) {
                    state.traceStartNodeId = null;
                    state.tracePath = null;
                    render(false);
                }
            }
        });

        if (dom.searchBtn) {
            dom.searchBtn.addEventListener("click", openSearchOverlay);
        }

        if (dom.searchInput) {
            dom.searchInput.addEventListener("keydown", e => {
                if (e.key === "Enter") {
                    const stmt = dom.searchInput.value.trim();
                    if (stmt.length >= 5) {
                        closeSearchOverlay();
                        verifyStatement(stmt);
                    }
                }
                if (e.key === "Escape") {
                    closeSearchOverlay();
                }
            });
        }

        // Click backdrop to close
        if (dom.searchOverlay) {
            dom.searchOverlay.addEventListener("click", e => {
                if (e.target === dom.searchOverlay) closeSearchOverlay();
            });
        }
    }

    function openSearchOverlay() {
        if (!dom.searchOverlay) return;
        dom.searchOverlay.classList.remove("hidden");
        setTimeout(() => dom.searchInput && dom.searchInput.focus(), 50);
    }

    function closeSearchOverlay() {
        if (!dom.searchOverlay) return;
        dom.searchOverlay.classList.add("hidden");
        if (dom.searchInput) dom.searchInput.value = "";
    }

    async function verifyStatement(statement) {
        // Show loading state in side panel immediately
        dom.detailPanel.classList.add("open");
        dom.panelTitle.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> Verifying…`;
        dom.panelBody.innerHTML = `
            <div class="panel-loading">
                <div class="loading-spinner"></div>
                <p>Checking statement against ${state.nodes.size} corpus claims…</p>
            </div>
        `;

        try {
            const url = `${CONFIG.api.base}/verify?statement=${encodeURIComponent(statement)}`;
            const res = await fetch(url);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            openVerificationPanel(data);
        } catch (err) {
            console.error("Verification failed:", err);
            dom.panelTitle.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> Verification`;
            dom.panelBody.innerHTML = `
                <div class="panel-error">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>Verification failed.</p>
                    <p class="panel-text" style="opacity:0.5">${esc(err.message)}</p>
                </div>
            `;
            showToast("Verification failed", "error");
        }
    }

    function openVerificationPanel(data) {
        dom.panelTitle.innerHTML = `<i class="fa-solid fa-scale-balanced"></i> Verification`;

        let html = "";

        // The statement being verified
        html += section("Statement", `
            <p class="panel-text verify-statement-text">"${esc(data.statement)}"</p>
        `);

        const total = data.total_claims_checked;

        if (total === 0) {
            html += `<div class="verify-empty">
                <i class="fa-solid fa-circle-info" style="font-size:24px;opacity:0.4"></i>
                <p>No relevant claims found in the corpus.</p>
                <p class="panel-text" style="opacity:0.6">Try uploading papers on this topic first.</p>
            </div>`;
            dom.panelBody.innerHTML = html;
            return;
        }

        // Summary row
        const nSup = data.supports.length;
        const nCon = data.contradicts.length;
        const nNeu = data.neutral.length;
        html += `<div class="verify-summary-row">
            ${nSup > 0 ? `<span class="verify-stat-chip supports">${nSup} support${nSup !== 1 ? "s" : ""}</span>` : ""}
            ${nCon > 0 ? `<span class="verify-stat-chip contradicts">${nCon} contradict${nCon !== 1 ? "s" : ""}</span>` : ""}
            ${nNeu > 0 ? `<span class="verify-stat-chip neutral">${nNeu} neutral</span>` : ""}
            <span class="verify-total-checked">${total} claim${total !== 1 ? "s" : ""} checked</span>
        </div>`;

        // Contradicts first (most interesting), then supports, then neutral
        if (nCon > 0) {
            html += section(
                `<i class="fa-solid fa-xmark" style="color:${CONFIG.colors.contradiction}"></i> Contradicts (${nCon})`,
                renderVerifyResults(data.contradicts)
            );
        }
        if (nSup > 0) {
            html += section(
                `<i class="fa-solid fa-check" style="color:${CONFIG.colors.finding}"></i> Supports (${nSup})`,
                renderVerifyResults(data.supports)
            );
        }
        if (nNeu > 0) {
            html += section(
                `<i class="fa-solid fa-minus" style="color:var(--text-muted)"></i> Neutral (${nNeu})`,
                renderVerifyResults(data.neutral)
            );
        }

        dom.panelBody.innerHTML = html;

        // Bind click on result items → navigate to that claim node in graph
        dom.panelBody.querySelectorAll(".verify-result-item[data-claim-id]").forEach(el => {
            el.addEventListener("click", () => {
                const node = state.nodes.get(el.dataset.claimId);
                if (node) {
                    openDetailPanel(node);
                    // Briefly highlight the node in the graph
                    state.selectedNodeId = node.id;
                    render(false);
                } else {
                    showToast("Claim not visible in current graph view", "info");
                }
            });
        });
    }

    function renderVerifyResults(results) {
        if (!results || results.length === 0) return "";
        return results.map(r => `
            <div class="verify-result-item" data-claim-id="${esc(r.claim_id)}"
                 title="Click to inspect this claim in the graph">
                <p class="verify-claim-text">${esc(r.claim_text)}</p>
                <div class="verify-claim-footer">
                    <span class="verify-paper-name">${esc(r.paper_title)}</span>
                    <span class="verify-sim">${Math.round(r.similarity_score * 100)}% match</span>
                </div>
                ${r.reason ? `<p class="verify-reason">${esc(r.reason)}</p>` : ""}
            </div>
        `).join("");
    }

// ─── Research Thread Tracer ───────────────────────────────────────────────

function handleTraceClick(node) {
    if (!state.traceStartNodeId) {
        // First node — mark as trace start
        state.traceStartNodeId = node.id;
        state.tracePath = null;
        render(false);
        showToast(
            `Trace start set — shift+click a second node to trace`,
            "info"
        );
    } else if (state.traceStartNodeId === node.id) {
        // Clicked same node — cancel
        state.traceStartNodeId = null;
        state.tracePath = null;
        render(false);
        showToast("Trace cancelled", "info");
    } else {
        // Second node — trigger trace
        const fromId = state.traceStartNodeId;
        state.traceStartNodeId = null;
        render(false);
        traceThread(fromId, node.id);
    }
}

async function traceThread(fromId, toId) {
    dom.detailPanel.classList.add("open");
    dom.panelTitle.innerHTML = `<i class="fa-solid fa-route"></i> Tracing…`;
    dom.panelBody.innerHTML = `
        <div class="panel-loading">
            <div class="loading-spinner"></div>
            <p>Finding reasoning chain…</p>
        </div>
    `;

    try {
        const url = `${CONFIG.api.base}/trace?from_id=${encodeURIComponent(fromId)}&to_id=${encodeURIComponent(toId)}`;
        const res = await fetch(url);

        if (res.status === 404) {
            dom.panelTitle.innerHTML = `<i class="fa-solid fa-route"></i> Thread Trace`;
            dom.panelBody.innerHTML = `
                <div class="verify-empty">
                    <i class="fa-solid fa-unlink" style="font-size:24px;opacity:0.4"></i>
                    <p>No connection found within 8 hops.</p>
                    <p class="panel-text" style="opacity:0.6">Try nodes that are more conceptually related.</p>
                </div>
            `;
            return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();

        // Highlight path in graph
        state.tracePath = {
            nodeIds: new Set(data.path_nodes.map(n => n.id)),
            edgeIds: new Set(data.path_edges.map(e => e.id).filter(Boolean)),
        };
        render(false);

        openTracePanel(data);

    } catch (err) {
        console.error("Trace failed:", err);
        dom.panelTitle.innerHTML = `<i class="fa-solid fa-route"></i> Thread Trace`;
        dom.panelBody.innerHTML = `
            <div class="panel-error">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>Trace failed.</p>
                <p class="panel-text" style="opacity:0.5">${esc(err.message)}</p>
            </div>
        `;
        showToast("Trace failed", "error");
    }
}

function openTracePanel(data) {
    dom.panelTitle.innerHTML = `<i class="fa-solid fa-route"></i> Thread Trace`;
    let html = "";

    // Path length summary
    html += section("Path", `
        <p class="panel-text">
            ${data.path_length} hop${data.path_length !== 1 ? "s" : ""} between nodes.
            <span style="opacity:0.5;font-size:11px">Press <kbd>Esc</kbd> to clear highlight.</span>
        </p>
    `);

    // Narrative
    if (data.narrative) {
        html += section("Reasoning", `
            <p class="panel-text trace-narrative">${esc(data.narrative)}</p>
        `);
    }

    // Step-by-step chain
    const edgeColorMap = {
        SUPPORTS: CONFIG.colors.supports,
        CONTRADICTS: CONFIG.colors.contradicts,
        EXTENDS: CONFIG.colors.extends,
        REPLICATES: CONFIG.colors.replicates,
        REFINES: CONFIG.colors.refines,
        CONTAINS: "var(--text-muted)",
        RELATES_TO: "var(--text-muted)",
    };
    const nodeColorMap = {
        Paper: CONFIG.colors.paper,
        Claim: CONFIG.colors.finding,
        Concept: CONFIG.colors.concept,
        OpenQuestion: CONFIG.colors.question,
    };

    let chainHtml = '<div class="trace-chain">';
    data.path_nodes.forEach((node, i) => {
        const nodeColor = nodeColorMap[node.label] || "#9aa0a8";
        const text = truncate(node.text || node.id, 80);

        chainHtml += `
            <div class="trace-node-chip" style="border-color:${nodeColor}">
                <span class="trace-node-badge" style="color:${nodeColor}">${esc(node.label)}</span>
                <span class="trace-node-text">${esc(text)}</span>
            </div>
        `;

        if (i < data.path_edges.length) {
            const edge = data.path_edges[i];
            const edgeType = (edge.edge_type || "UNKNOWN");
            const edgeColor = edgeColorMap[edgeType] || "var(--text-muted)";
            chainHtml += `
                <div class="trace-connector">
                    <div class="trace-connector-line" style="background:${edgeColor}40"></div>
                    <span class="trace-edge-type" style="color:${edgeColor};border-color:${edgeColor}50">
                        ${esc(edgeType)}
                    </span>
                    <div class="trace-connector-line" style="background:${edgeColor}40"></div>
                </div>
            `;
        }
    });
    chainHtml += '</div>';
    html += section("Chain", chainHtml);

    dom.panelBody.innerHTML = html;
}

// ─── Literature Review Generator ─────────────────────────────────────────

// Stores the current review data for the download button
let _currentReview = null;

function initReview() {
    if (!dom.reviewBtn || !dom.reviewModal) return; // safety

    dom.reviewBtn.addEventListener("click", generateReview);

    if (dom.reviewCloseBtn) {
        dom.reviewCloseBtn.addEventListener("click", closeReviewModal);
    }

    if (dom.reviewDownloadBtn) {
        dom.reviewDownloadBtn.addEventListener("click", () => {
            if (_currentReview) downloadReviewDocx(_currentReview);
        });
    }

    // Click backdrop to close
    dom.reviewModal.addEventListener("click", e => {
        if (e.target === dom.reviewModal) closeReviewModal();
    });

    // Esc to close
    document.addEventListener("keydown", e => {
        if (e.key === "Escape" && dom.reviewModal && !dom.reviewModal.classList.contains("hidden")) {
            closeReviewModal();
        }
    });
}

function openReviewModal() {
    if (!dom.reviewModal) return;
    dom.reviewModal.classList.remove("hidden");
}

function closeReviewModal() {
    if (!dom.reviewModal) return;
    dom.reviewModal.classList.add("hidden");
}

async function generateReview() {
    if (!dom.reviewModal || !dom.reviewContent) return;

    openReviewModal();
    _currentReview = null;

    if (dom.reviewDownloadBtn) dom.reviewDownloadBtn.disabled = true;
    if (dom.reviewModalHeading) dom.reviewModalHeading = document.getElementById("review-modal-heading");

    dom.reviewContent.innerHTML = `
        <div class="review-loading">
            <div class="loading-spinner" style="width:32px;height:32px;border-width:3px"></div>
            <p>Analyzing corpus and generating review…</p>
            <p class="review-loading-hint">This may take 10–20 seconds.</p>
        </div>
    `;

    try {
        const res = await fetch(`${CONFIG.api.base}/generate/review`, { method: "POST" });
        if (res.status === 400) {
            const err = await res.json();
            dom.reviewContent.innerHTML = `
                <div class="review-empty">
                    <i class="fa-solid fa-circle-info"></i>
                    <p>${esc(err.detail || "No papers available.")}</p>
                </div>
            `;
            return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        _currentReview = data.review;
        renderReview(data);

        if (dom.reviewDownloadBtn) dom.reviewDownloadBtn.disabled = false;

    } catch (err) {
        console.error("Review generation failed:", err);
        dom.reviewContent.innerHTML = `
            <div class="review-empty">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>Review generation failed.</p>
                <p style="opacity:0.5;font-size:12px">${esc(err.message)}</p>
            </div>
        `;
        showToast("Review generation failed", "error");
    }
}

function renderReview(data) {
    const review = data.review;
    const heading = document.getElementById("review-modal-heading");
    if (heading) heading.textContent = review.title || "Literature Review";

    let html = `<div class="review-document">`;

    // Title page area
    html += `<h1 class="review-title">${esc(review.title || "Literature Review")}</h1>`;
    html += `<p class="review-meta">${data.paper_count} paper${data.paper_count !== 1 ? "s" : ""} · Generated ${new Date().toLocaleDateString()}</p>`;

    // Abstract
    if (review.abstract) {
        html += `<div class="review-abstract">
            <h2 class="review-section-heading">Abstract</h2>
            <p class="review-body-text">${esc(review.abstract)}</p>
        </div>`;
    }

    // Sections
    for (const sec of (review.sections || [])) {
        html += `<div class="review-section">
            <h2 class="review-section-heading">${esc(sec.heading)}</h2>
            <p class="review-body-text">${esc(sec.content)}</p>
        </div>`;
    }

    // References
    if (review.references && review.references.length > 0) {
        html += `<div class="review-references">
            <h2 class="review-section-heading review-references-heading">References</h2>
            <ul class="review-ref-list">`;
        for (const ref of review.references) {
            html += `<li class="review-ref-item">${esc(ref)}</li>`;
        }
        html += `</ul></div>`;
    }

    html += `</div>`;
    dom.reviewContent.innerHTML = html;
}

async function downloadReviewDocx(review) {
    if (dom.reviewDownloadBtn) {
        dom.reviewDownloadBtn.disabled = true;
        dom.reviewDownloadBtn.innerHTML = `<div class="loading-spinner" style="width:14px;height:14px;border-width:2px;margin:0"></div> Generating…`;
    }

    try {
        const res = await fetch(`${CONFIG.api.base}/generate/review/docx`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ review }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = (review.title || "literature_review")
            .toLowerCase().replace(/\s+/g, "_").substring(0, 50) + ".docx";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

    } catch (err) {
        console.error("Download failed:", err);
        showToast("Download failed", "error");
    } finally {
        if (dom.reviewDownloadBtn) {
            dom.reviewDownloadBtn.disabled = false;
            dom.reviewDownloadBtn.innerHTML = `<i class="fa-solid fa-file-word"></i> Download .docx`;
        }
    }
}

    function openDetailPanel(node) {
        state.selectedNodeId = node.id;
        dom.detailPanel.classList.add("open");

        const color = getNodeColor(node);
        let html = "";

        if (node.label === "Paper") {
            dom.panelTitle.innerHTML = '<i class="fa-solid fa-file-lines"></i> Paper';
            html += badge("Paper", "paper");
            if (node.status) html += badge(node.status, statusBadgeClass(node.status));
            html += section("Title", `<p class="panel-text"><strong>${esc(node.title || "Untitled")}</strong></p>`);
            if (node.authors && node.authors.length) {
                html += section("Authors", `<p class="panel-text">${esc(node.authors.join(", "))}</p>`);
            }
            if (node.year) {
                html += section("Year", `<p class="panel-text">${esc(String(node.year))}</p>`);
            }
            if (node.abstract) {
                html += section("Abstract", `<p class="panel-text">${esc(node.abstract)}</p>`);
            }
        } else if (node.label === "Claim") {
            dom.panelTitle.innerHTML = '<i class="fa-solid fa-lightbulb"></i> Claim';
            html += badge(node.type || "finding", esc(`type-${(node.type || "finding").toLowerCase()}`));
            if (node.section) html += badge(node.section, "type-paper");
            html += section("Claim", `<p class="panel-text">${esc(node.text || "")}</p>`);
            if (node.confidence !== undefined) {
                const pct = Math.round(node.confidence * 100);
                const barColor = node.confidence > 0.7 ? CONFIG.colors.finding
                    : node.confidence > 0.4 ? CONFIG.colors.method
                    : CONFIG.colors.contradiction;
                html += section("Confidence", `
                    <div class="confidence-meter">
                        <div class="confidence-bar-bg">
                            <div class="confidence-bar-fill" style="width:${pct}%;background:${barColor}"></div>
                        </div>
                        <span class="confidence-value">${pct}%</span>
                    </div>
                `);
            }
        // ── Field Consensus Meter ──────────────────────────────
        const consensus = computeConsensus(node.id);
        if (consensus === null) {
            html += section("Field Consensus", `
                <p class="panel-text consensus-empty">
                    <i class="fa-solid fa-circle-info" style="opacity:0.5"></i>
                    No cross-paper data yet — upload more papers on the same topic.
                </p>
            `);
        } else {
            const pct = consensus.consensusPct;
            const barColor = pct >= 70 ? CONFIG.colors.finding
                : pct >= 40 ? CONFIG.colors.method
                : CONFIG.colors.contradiction;

            const parts = [];
            if (consensus.supportCount > 0)
                parts.push(`${consensus.supportCount} support${consensus.supportCount > 1 ? "s" : ""}`);
            if (consensus.disputeCount > 0)
                parts.push(`${consensus.disputeCount} dispute${consensus.disputeCount > 1 ? "s" : ""}`);
            if (consensus.extendCount > 0)
                parts.push(`${consensus.extendCount} extend${consensus.extendCount > 1 ? "s" : ""}`);

            const label = pct >= 70 ? "Consensus" : pct >= 40 ? "Contested" : "Disputed";

            html += section("Field Consensus", `
                <div class="consensus-meter">
                    <div class="confidence-meter">
                        <div class="confidence-bar-bg">
                            <div class="confidence-bar-fill" style="width:${pct}%;background:${barColor}"></div>
                        </div>
                        <span class="confidence-value">${pct}%</span>
                    </div>
                    <div class="consensus-footer">
                        <span class="consensus-label" style="color:${barColor}">${esc(label)}</span>
                        <span class="consensus-breakdown">${esc(parts.join(" · "))}</span>
                    </div>
                    <div class="consensus-explain-area">
                        <button class="consensus-explain-btn"
                                data-claim-id="${esc(node.id)}"
                                data-consensus-pct="${pct}">
                            <i class="fa-solid fa-wand-magic-sparkles"></i> Ask AI to explain
                        </button>
                        <div class="consensus-explanation hidden"></div>
                    </div>
                </div>
            `);
        }
        // ── End Field Consensus Meter ──────────────────────────
            if (node.source_chunk_text) {
                html += section("Source Text", `<p class="panel-text" style="font-style:italic;opacity:0.8">"${esc(node.source_chunk_text)}"</p>`);
            }
        } else if (node.label === "OpenQuestion") {
            dom.panelTitle.innerHTML = '<i class="fa-solid fa-circle-question"></i> Open Question';
            html += badge("Question", "type-question");
            if (node.status) html += badge(node.status, "type-paper");
            html += section("Question", `<p class="panel-text"><strong>${esc(node.question || "")}</strong></p>`);
            if (node.novelty_score !== undefined) {
                const pct = Math.round(node.novelty_score * 100);
                html += section("Novelty Score", `
                    <div class="confidence-meter">
                        <div class="confidence-bar-bg">
                            <div class="confidence-bar-fill" style="width:${pct}%;background:${CONFIG.colors.question}"></div>
                        </div>
                        <span class="confidence-value">${pct}%</span>
                    </div>
                `);
            }
            if (node.web_evidence) {
                html += section("Web Evidence", `<p class="panel-text">${esc(node.web_evidence)}</p>`);
            }
        } else if (node.label === "Concept") {
            dom.panelTitle.innerHTML = '<i class="fa-solid fa-bolt"></i> Concept';
            html += badge("Concept", "type-concept");
            html += section("Name", `<p class="panel-text"><strong>${esc(node.name || "")}</strong></p>`);
        }

        // Show connected edges
        const connections = getConnections(node.id);
        if (connections.length > 0) {
            let connHtml = "";
            connections.forEach(conn => {
                const otherNode = state.nodes.get(conn.otherId);
                const typeColor = CONFIG.colors[conn.edgeType] || CONFIG.colors.replicates;
                const label = otherNode ? getNodeLabel(otherNode) : conn.otherId.slice(0, 8);
                connHtml += `
                    <div class="connection-item" data-node-id="${esc(conn.otherId)}">
                        <span class="connection-dot" style="background:${otherNode ? getNodeColor(otherNode) : '#666'}"></span>
                        <span class="connection-label">${esc(label)}</span>
                        <span class="connection-type" style="color:${typeColor};border:1px solid ${typeColor}33;background:${typeColor}15">${esc(conn.edgeType)}</span>
                    </div>
                `;
            });
            html += section(`Connections (${connections.length})`, connHtml);
        }

        dom.panelBody.innerHTML = html;

        // Bind consensus explain button
        const explainBtn = dom.panelBody.querySelector(".consensus-explain-btn");
        if (explainBtn) {
            explainBtn.addEventListener("click", () => {
                const claimId = explainBtn.dataset.claimId;
                const pct = parseInt(explainBtn.dataset.consensusPct, 10);
                explainConsensus(claimId, pct, explainBtn);
            });
        }

        // Bind connection clicks
        dom.panelBody.querySelectorAll(".connection-item").forEach(el => {
            el.addEventListener("click", () => {
                const nodeId = el.dataset.nodeId;
                const targetNode = state.nodes.get(nodeId);
                if (targetNode) openDetailPanel(targetNode);
            });
        });
    }

    async function openEdgeDetailPanel(edge) {
        // Show loading state immediately
        dom.detailPanel.classList.add("open");
        dom.panelTitle.innerHTML = `<i class="fa-solid fa-arrow-right-arrow-left"></i> Relationship`;
        dom.panelBody.innerHTML = `
            <div class="panel-loading">
                <div class="loading-spinner"></div>
                <p>Loading relationship details…</p>
            </div>
        `;

        try {
            const res = await fetch(`${CONFIG.api.base}/edge/${encodeURIComponent(edge.id)}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            const { edge: e, source_claim, target_claim, source_paper, target_paper } = data;
            const edgeType = (e.type || "supports").toLowerCase();
            const edgeColor = CONFIG.colors[edgeType] || CONFIG.colors.replicates;
            const strengthPct = Math.round((e.strength || 0) * 100);

            // Set panel title with colored edge type badge
            dom.panelTitle.innerHTML = `<i class="fa-solid fa-arrow-right-arrow-left"></i> Relationship`;

            let html = "";

            // Edge type badge + strength
            html += `<div class="panel-badges">
                ${badge(edgeType.toUpperCase(), esc(`edge-badge edge-type-${edgeType}`))}
            </div>`;

            // Strength bar
            html += section("Strength", `
                <div class="confidence-meter">
                    <div class="confidence-bar-bg">
                        <div class="confidence-bar-fill"
                             style="width:${strengthPct}%;background:${edgeColor}"></div>
                    </div>
                    <span class="confidence-value">${strengthPct}%</span>
                </div>
            `);

            // Reasoning
            if (e.reasoning) {
                html += section("Agent Reasoning", `
                    <p class="panel-text reasoning-text">${esc(e.reasoning)}</p>
                `);
            }

            // Two claims side by side
            html += `<div class="claims-comparison">
                <div class="claim-card claim-card-source">
                    <div class="claim-card-header">
                        <span class="claim-card-label source-label">
                            <i class="fa-solid fa-arrow-up-from-bracket"></i> Source Claim
                        </span>
                        <span class="claim-card-paper">${esc(source_paper.title || "Unknown paper")}</span>
                        ${source_paper.year ? `<span class="claim-card-year">${esc(String(source_paper.year))}</span>` : ""}
                    </div>
                    <p class="claim-card-text">${esc(source_claim.text || "")}</p>
                    <div class="claim-card-meta">
                        ${badge(source_claim.type || "finding", esc(`type-${(source_claim.type || "finding").toLowerCase()}`))}
                        ${badge(source_claim.section || "unknown", "type-paper")}
                        <span class="claim-confidence">${Math.round((source_claim.confidence || 0) * 100)}% confidence</span>
                    </div>
                    ${source_claim.source_chunk_text ? `
                    <details class="source-chunk-details">
                        <summary>Source text</summary>
                        <p class="panel-text source-chunk-text">${esc(source_claim.source_chunk_text)}</p>
                    </details>` : ""}
                </div>

                <div class="claims-vs-divider">
                    <div class="vs-line"></div>
                    <span class="vs-badge" style="color:${edgeColor};border-color:${edgeColor}">
                        ${esc(edgeType.toUpperCase())}
                    </span>
                    <div class="vs-line"></div>
                </div>

                <div class="claim-card claim-card-target">
                    <div class="claim-card-header">
                        <span class="claim-card-label target-label">
                            <i class="fa-solid fa-arrow-down-to-bracket"></i> Target Claim
                        </span>
                        <span class="claim-card-paper">${esc(target_paper.title || "Unknown paper")}</span>
                        ${target_paper.year ? `<span class="claim-card-year">${esc(String(target_paper.year))}</span>` : ""}
                    </div>
                    <p class="claim-card-text">${esc(target_claim.text || "")}</p>
                    <div class="claim-card-meta">
                        ${badge(target_claim.type || "finding", esc(`type-${(target_claim.type || "finding").toLowerCase()}`))}
                        ${badge(target_claim.section || "unknown", "type-paper")}
                        <span class="claim-confidence">${Math.round((target_claim.confidence || 0) * 100)}% confidence</span>
                    </div>
                    ${target_claim.source_chunk_text ? `
                    <details class="source-chunk-details">
                        <summary>Source text</summary>
                        <p class="panel-text source-chunk-text">${esc(target_claim.source_chunk_text)}</p>
                    </details>` : ""}
                </div>
            </div>`;

            dom.panelBody.innerHTML = html;

        } catch (err) {
            console.error("Failed to load edge detail:", err);
            dom.panelBody.innerHTML = `
                <div class="panel-error">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>Could not load relationship details.</p>
                    <p class="panel-text" style="opacity:0.5">${esc(err.message)}</p>
                </div>
            `;
        }
    }

    async function explainConsensus(claimId, consensusPct, btn) {
        // Disable button and show loading state
        btn.disabled = true;
        btn.innerHTML = `<div class="loading-spinner" style="width:14px;height:14px;border-width:2px;margin:0"></div> Analyzing…`;

        const explanationDiv = btn.closest(".consensus-explain-area").querySelector(".consensus-explanation");
        explanationDiv.classList.add("hidden");
        explanationDiv.textContent = "";

        try {
            const res = await fetch(
                `${CONFIG.api.base}/claim/${encodeURIComponent(claimId)}/consensus/explain`
            );
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            explanationDiv.textContent = data.explanation;
            explanationDiv.classList.remove("hidden");
            explanationDiv.classList.add("consensus-explanation-appear");

            // Replace button with a subtle re-ask option
            btn.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Re-explain`;
            btn.disabled = false;

        } catch (err) {
            console.error("Consensus explain failed:", err);
            btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Ask AI to explain`;
            btn.disabled = false;
            showToast("Could not generate explanation", "error");
        }
    }

    function getConnections(nodeId) {
        const conns = [];
        state.edges.forEach(e => {
            const srcId = typeof e.source === "object" ? e.source.id : (e.source_claim_id || e.source);
            const tgtId = typeof e.target === "object" ? e.target.id : (e.target_claim_id || e.target);
            if (srcId === nodeId) {
                conns.push({ otherId: tgtId, edgeType: e.type, direction: "outgoing" });
            } else if (tgtId === nodeId) {
                conns.push({ otherId: srcId, edgeType: e.type, direction: "incoming" });
            }
        });
        return conns;
    }

    function closeDetailPanel() {
        dom.detailPanel.classList.remove("open");
        state.selectedNodeId = null;
    }

    function bindPanelClose() {
        dom.panelClose.addEventListener("click", closeDetailPanel);
        // Click on SVG background closes panel
        state.svg.on("click", () => closeDetailPanel());
    }

    // Panel HTML helpers
    function section(title, content) {
        return `<div class="panel-section"><div class="panel-section-title">${title}</div>${content}</div>`;
    }

    function badge(text, cls) {
        return `<span class="panel-badge ${cls}">${esc(text)}</span>`;
    }

    function statusBadgeClass(status) {
        const s = (status || "").toLowerCase();
        if (s === "complete") return "type-finding";
        if (s === "error") return "type-limitation";
        if (s === "queued") return "type-paper";
        return "type-paper";
    }

    function esc(str) {
        if (!str) return "";
        const el = document.createElement("span");
        el.textContent = str;
        return el.innerHTML;
    }

    // ─── Fetch Initial Graph ───
    async function fetchInitialGraph() {
        try {
            const res = await fetch(`${CONFIG.api.base}${CONFIG.api.graphEndpoint}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            // Process nodes
            if (data.nodes) {
                data.nodes.forEach(n => {
                    normalizeNode(n);
                    state.nodes.set(n.id, n);
                });
            }

            // Process edges
            if (data.edges) {
                data.edges.forEach(e => {
                    state.edges.set(e.id, e);
                });
            }

            // Also handle questions if separate
            if (data.questions) {
                data.questions.forEach(q => {
                    q.label = "OpenQuestion";
                    state.nodes.set(q.id, q);
                });
            }

            render(false);
        } catch (err) {
            console.warn("Could not fetch initial graph — starting empty:", err.message);
        }
    }

    function normalizeNode(n) {
        // Ensure a label is set
        if (!n.label) {
            if (n.title !== undefined) n.label = "Paper";
            else if (n.text !== undefined && n.type !== undefined) n.label = "Claim";
            else if (n.question !== undefined) n.label = "OpenQuestion";
            else if (n.name !== undefined) n.label = "Concept";
            else n.label = "Paper";
        }
    }

    // ─── WebSocket ───
    function connectWebSocket() {
        if (state.ws && state.ws.readyState <= 1) return;

        setWsStatus("reconnecting");

        try {
            state.ws = new WebSocket(CONFIG.api.ws);
        } catch (e) {
            console.error("WS connection error:", e);
            scheduleReconnect();
            return;
        }

        state.ws.onopen = () => {
            console.log("✅ WebSocket connected");
            setWsStatus("connected");
            state.wsReconnectDelay = CONFIG.ws.reconnectDelay; // reset backoff
        };

        state.ws.onclose = () => {
            console.warn("WebSocket closed");
            setWsStatus("disconnected");
            scheduleReconnect();
        };

        state.ws.onerror = (err) => {
            console.error("WebSocket error:", err);
            state.ws.close();
        };

        state.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleWsEvent(msg);
            } catch (e) {
                console.warn("Failed to parse WS message:", e);
            }
        };
    }

    function scheduleReconnect() {
        if (state.wsReconnectTimer) clearTimeout(state.wsReconnectTimer);
        state.wsReconnectTimer = setTimeout(() => {
            connectWebSocket();
        }, state.wsReconnectDelay);
        // Exponential backoff
        state.wsReconnectDelay = Math.min(
            state.wsReconnectDelay * CONFIG.ws.reconnectBackoff,
            CONFIG.ws.maxReconnectDelay
        );
    }

    function setWsStatus(status) {
        dom.wsIndicator.className = `ws-indicator ${status}`;
        const labels = { connected: "Connected", disconnected: "Disconnected", reconnecting: "Reconnecting…" };
        dom.wsLabel.textContent = labels[status] || status;
    }

    // ─── WebSocket Event Handlers ───
    function handleWsEvent(msg) {
        const { type, data } = msg;

        switch (type) {
            case "node_added":
                handleNodeAdded(data);
                break;
            case "edge_added":
                handleEdgeAdded(data);
                break;
            case "edge_updated":
                handleEdgeUpdated(data);
                break;
            case "question_added":
                handleQuestionAdded(data);
                break;
            case "question_resolved":
                handleQuestionResolved(data);
                break;
            case "paper_status":
                handlePaperStatus(data);
                break;
            default:
                console.log("Unknown WS event:", type, data);
        }
    }

    function handleNodeAdded(data) {
        const node = data.node || data;
        normalizeNode(node);
        const existing = state.nodes.get(node.id);
        if (existing) {
            Object.assign(existing, node);
        } else {
            state.nodes.set(node.id, node);
        }
        render(true);
        showToast(`New ${node.label}: ${getNodeLabel(node)}`, "info");
    }

    function handleEdgeAdded(data) {
        const edge = data.edge || data;
        if (!edge.source) edge.source = edge.source_claim_id;
        if (!edge.target) edge.target = edge.target_claim_id;
        
        state.edges.set(edge.id, edge);
        render(true);

        if (edge.type === "contradicts") {
            showToast("⚡ Contradiction detected!", "error");
        }
        
        // Refresh panel if affected
        if (state.selectedNodeId) {
            const srcId = typeof edge.source === "object" ? edge.source.id : (edge.source_claim_id || edge.source);
            const tgtId = typeof edge.target === "object" ? edge.target.id : (edge.target_claim_id || edge.target);
            if (srcId === state.selectedNodeId || tgtId === state.selectedNodeId) {
                const node = state.nodes.get(state.selectedNodeId);
                if (node) openDetailPanel(node);
            }
        }
    }

    function handleEdgeUpdated(data) {
        const edge = data.edge || data;
        if (!edge.source) edge.source = edge.source_claim_id;
        if (!edge.target) edge.target = edge.target_claim_id;
        const existing = state.edges.get(edge.id);
        if (existing) {
            Object.assign(existing, edge);
        } else {
            state.edges.set(edge.id, edge);
        }
        render(false);
    }

    function handleQuestionAdded(data) {
        // If data is wrapped, extract it. Otherwise data is the object.
        // We must be careful because data.question is the string text!
        const q = (data.question && typeof data.question === "object") ? data.question : data;
        q.label = "OpenQuestion";
        state.nodes.set(q.id, q);
        render(true);
        showToast(`❓ New question: ${truncate(q.question, 50)}`, "info");
    }

    function handleQuestionResolved(data) {
        const qId = data.question_id || data.id;
        const q = state.nodes.get(qId);
        if (q) {
            q.status = "resolved";
            render(false);
            showToast("✅ Question resolved", "success");
        }
    }

    function handlePaperStatus(data) {
        const { paper_id, status } = data;
        const paperNode = state.nodes.get(paper_id);
        if (paperNode) {
            paperNode.status = status;
        }
        setPipelineStatus(status);

        if (status === "complete") {
            showToast("🎉 Paper analysis complete!", "success");
            // Refresh the detail panel to recalculate consensus and connections
            if (state.selectedNodeId) {
                const selectedNode = state.nodes.get(state.selectedNodeId);
                if (selectedNode) openDetailPanel(selectedNode);
            }
        } else if (status === "error") {
            showToast("⚠️ Error processing paper", "error");
        }
    }

    function setPipelineStatus(status) {
        const s = (status || "").toLowerCase();
        const statusDot = dom.statusDot;
        statusDot.className = "status-dot";

        const displayNames = {
            queued: "Queued",
            extracting: "Extracting Claims…",
            claims_ready: "Claims Ready",
            comparing: "Comparing Claims…",
            edges_ready: "Edges Ready",
            gap_finding: "Finding Gaps…",
            complete: "Complete",
            error: "Error",
        };

        dom.statusLabel.textContent = displayNames[s] || status || "Ready";

        if (["extracting", "comparing", "gap_finding", "queued"].includes(s)) {
            statusDot.classList.add("processing");
        } else if (s === "complete") {
            statusDot.classList.add("complete");
            // Reset to idle after 5 seconds
            setTimeout(() => {
                statusDot.className = "status-dot idle";
                dom.statusLabel.textContent = "Ready";
            }, 5000);
        } else if (s === "error") {
            statusDot.classList.add("error");
        } else {
            statusDot.classList.add("idle");
        }
    }

    // ─── Upload ───
    function bindUpload() {
        const dropzone = dom.uploadDropzone;
        const fileInput = dom.fileInput;

        // Click to browse
        dropzone.addEventListener("click", (e) => {
            if (e.target === fileInput) return;
            fileInput.click();
        });

        fileInput.addEventListener("change", () => {
            if (fileInput.files.length > 0) {
                uploadFile(fileInput.files[0]);
            }
        });

        // Drag & drop
        dropzone.addEventListener("dragenter", (e) => {
            e.preventDefault();
            dropzone.classList.add("drag-over");
        });

        dropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropzone.classList.add("drag-over");
        });

        dropzone.addEventListener("dragleave", (e) => {
            e.preventDefault();
            dropzone.classList.remove("drag-over");
        });

        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropzone.classList.remove("drag-over");
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
                    uploadFile(file);
                } else {
                    showToast("Please upload a PDF file", "error");
                }
            }
        });
    }

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);

        dom.uploadContent.style.display = "none";
        dom.uploadProgress.classList.remove("hidden");
        dom.progressFill.style.width = "0%";
        dom.uploadStatusText.textContent = `Uploading ${file.name}…`;

        try {
            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener("progress", (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 100);
                    dom.progressFill.style.width = `${pct}%`;
                    dom.uploadStatusText.textContent = `Uploading… ${pct}%`;
                }
            });

            const result = await new Promise((resolve, reject) => {
                xhr.open("POST", `${CONFIG.api.base}${CONFIG.api.uploadEndpoint}`);

                xhr.onload = () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        resolve(JSON.parse(xhr.responseText));
                    } else {
                        reject(new Error(`Upload failed: HTTP ${xhr.status}`));
                    }
                };
                xhr.onerror = () => reject(new Error("Network error during upload"));
                xhr.send(formData);
            });

            dom.progressFill.style.width = "100%";
            dom.uploadStatusText.textContent = "Processing…";
            showToast(`📄 Paper uploaded! ID: ${result.paper_id || "OK"}`, "success");
            setPipelineStatus(result.status || "queued");

            // Reset upload UI after a delay
            setTimeout(resetUploadUI, 2500);

        } catch (err) {
            console.error("Upload error:", err);
            dom.uploadStatusText.textContent = "Upload failed";
            dom.progressFill.style.width = "0%";
            showToast(`Upload failed: ${err.message}`, "error");
            setTimeout(resetUploadUI, 3000);
        }

        // Reset file input
        dom.fileInput.value = "";
    }

    function resetUploadUI() {
        dom.uploadContent.style.display = "";
        dom.uploadProgress.classList.add("hidden");
        dom.progressFill.style.width = "0%";
    }

    // ─── Toast Notifications ───
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        dom.toastContainer.appendChild(toast);

        // Auto-remove
        setTimeout(() => {
            toast.classList.add("toast-out");
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // ─── Window resize handler ───
    window.addEventListener("resize", () => {
        const width = dom.svg.clientWidth;
        const height = dom.svg.clientHeight;
        if (state.simulation) {
            state.simulation.force("center", d3.forceCenter(width / 2, height / 2).strength(CONFIG.graph.centerStrength));
            state.simulation.alpha(0.1).restart();
        }
    });

    // ─── Boot ───
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();
