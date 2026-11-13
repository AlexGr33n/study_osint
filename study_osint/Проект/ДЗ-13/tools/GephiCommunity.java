// Gephi без GUI (Toolkit 0.11.4): ті самі кроки, що в завданні 4 через GUI —
// імпорт вузлів/ребер, ForceAtlas2 (Approximate Repulsion = Barnes-Hut) → Prevent Overlap (adjustSizes),
// колір = Partition за class, розмір = Ranking за pagerank, Preview → PNG/SVG, Save project → .gephi.
// Запуск: java --add-opens java.base/java.net=ALL-UNNAMED -cp gephi-toolkit-0.11.4-all.jar GephiCommunity.java nodes.csv edges.csv outDir
// Без -Djava.awt.headless=true: PNG-експортер Gephi падає з HeadlessException, потрібен дисплей.
import java.awt.Color;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.gephi.appearance.api.*;
import org.gephi.appearance.plugin.*;
import org.gephi.graph.api.*;
import org.gephi.io.exporter.api.ExportController;
import org.gephi.io.exporter.preview.PNGExporter;
import org.gephi.layout.plugin.forceAtlas2.*;
import org.gephi.preview.api.*;
import org.gephi.preview.types.EdgeColor;
import org.gephi.project.api.ProjectController;
import org.openide.util.Lookup;

public class GephiCommunity {
    static List<String[]> csv(String path) throws IOException {
        List<String[]> rows = new ArrayList<>();
        for (String line : Files.readAllLines(Path.of(path), StandardCharsets.UTF_8)) {
            if (line.isBlank()) continue;
            rows.add(line.replace("\"", "").split(",", -1)); // shortcut: значення без ком (адреси, числа), інакше потрібен CSV-парсер
        }
        return rows.subList(1, rows.size());
    }

    public static void main(String[] a) throws Exception {
        String out = a[2];
        ProjectController pc = Lookup.getDefault().lookup(ProjectController.class);
        pc.newProject();
        GraphModel gm = Lookup.getDefault().lookup(GraphController.class).getGraphModel(pc.getCurrentWorkspace());
        Table nt = gm.getNodeTable();
        Column cClass = nt.addColumn("class", String.class);
        Column cPr = nt.addColumn("pagerank", Double.class);
        Column cFirst = nt.addColumn("firstStep", Integer.class);
        DirectedGraph g = gm.getDirectedGraph();
        GraphFactory f = gm.factory();
        Random rnd = new Random(42);

        for (String[] r : csv(a[0])) { // Id,class,community,pagerank,firstStep,lastStep
            Node n = f.newNode(r[0]);
            n.setLabel(r[0]);
            n.setAttribute(cClass, r[1].equals("1") ? "illicit" : r[1].equals("2") ? "licit" : "unknown");
            n.setAttribute(cPr, Double.parseDouble(r[3]));
            if (!r[4].isEmpty()) n.setAttribute(cFirst, Integer.parseInt(r[4]));
            n.setX(rnd.nextFloat() * 1000 - 500);
            n.setY(rnd.nextFloat() * 1000 - 500);
            g.addNode(n);
        }
        int edges = 0;
        for (String[] r : csv(a[1])) { // Source,Target,Weight
            Node s = g.getNode(r[0]), t = g.getNode(r[1]);
            if (s == null || t == null) continue;
            g.addEdge(f.newEdge(s, t, 0, Double.parseDouble(r[2]), true));
            edges++;
        }
        System.out.println("nodes=" + g.getNodeCount() + " edges=" + edges);

        // Appearance: колір і розмір (розмір ставимо до Prevent Overlap, щоб layout враховував його)
        AppearanceController ac = Lookup.getDefault().lookup(AppearanceController.class);
        AppearanceModel am = ac.getModel();
        Function colorF = am.getNodeFunction(cClass, PartitionElementColorTransformer.class);
        Partition p = ((PartitionFunction) colorF).getPartition();
        p.setColor("illicit", new Color(0xD7, 0x26, 0x1E));
        p.setColor("licit", new Color(0x1F, 0x78, 0xB4));
        p.setColor("unknown", new Color(0xBD, 0xBD, 0xBD));
        ac.transform(colorF);
        Function sizeF = am.getNodeFunction(cPr, RankingNodeSizeTransformer.class);
        RankingNodeSizeTransformer st = (RankingNodeSizeTransformer) sizeF.getTransformer();
        st.setMinSize(3f);
        st.setMaxSize(25f);
        ac.transform(sizeF);

        ForceAtlas2 fa = new ForceAtlas2Builder().buildLayout();
        fa.setGraphModel(gm);
        fa.resetPropertiesValues();
        fa.setInitialisationSeed(42);
        fa.setBarnesHutOptimize(true);   // Approximate Repulsion
        fa.setScalingRatio(10.0);
        fa.setStrongGravityMode(true);   // інакше дерева-ланцюжки розлітаються, а вузли стають крапками
        fa.setGravity(1.0);
        fa.setThreadsCount(8);
        fa.initAlgo();
        for (int i = 0; i < 1500 && fa.canAlgo(); i++) fa.goAlgo();
        fa.setAdjustSizes(true);         // Prevent Overlap
        for (int i = 0; i < 300 && fa.canAlgo(); i++) fa.goAlgo();
        fa.endAlgo();

        PreviewModel pm = Lookup.getDefault().lookup(PreviewController.class).getModel();
        PreviewProperties pp = pm.getProperties();
        pp.putValue(PreviewProperty.SHOW_NODE_LABELS, false); // 78 адрес нечитабельні; хаби названо в підписі звіту
        pp.putValue(PreviewProperty.EDGE_CURVED, false);
        pp.putValue(PreviewProperty.EDGE_OPACITY, 35f);
        pp.putValue(PreviewProperty.EDGE_THICKNESS, 0.6f);
        pp.putValue(PreviewProperty.EDGE_COLOR, new EdgeColor(EdgeColor.Mode.SOURCE));
        pp.putValue(PreviewProperty.NODE_BORDER_WIDTH, 0.3f);
        pp.putValue(PreviewProperty.BACKGROUND_COLOR, Color.WHITE);

        ExportController ec = Lookup.getDefault().lookup(ExportController.class);
        ec.exportFile(new File(out, "community.svg"));
        PNGExporter png = (PNGExporter) ec.getExporter("png");
        png.setWidth(2400);
        png.setHeight(2400);
        png.setWorkspace(pc.getCurrentWorkspace());
        ec.exportFile(new File(out, "community.png"), png);
        pc.saveProject(pc.getCurrentProject(), new File(out, "community.gephi"));
        System.out.println("saved to " + out);
        System.exit(0);
    }
}
