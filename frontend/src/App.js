import "@/App.css";

function App() {
  const fileUrl = "/nocturne-cleaned.html";

  const removed = [
    "Google Analytics (gtag) inline script",
    "effectivecpmnetwork.com ad <script>",
    "CPM ad self-reinjection setInterval",
    "Google Fonts external stylesheet + preconnects",
  ];

  return (
    <div className="page" data-testid="cleanup-result-page">
      <div className="wrap">
        <div className="tag">static html ad cleanup · result</div>
        <h1>
          <span className="mono">index.html</span> is clean.
        </h1>
        <p className="lede">
          The Nocturne launcher HTML pulled from the <span className="mono">mathlearning</span> zip
          has been stripped of its ads, trackers, and monetization layer. Layout preserved, single self-contained file.
        </p>

        <div className="grid">
          <a
            className="btn primary"
            href={fileUrl}
            target="_blank"
            rel="noreferrer"
            data-testid="preview-link"
          >
            Open the cleaned page →
          </a>
          <a
            className="btn ghost"
            href={fileUrl}
            download="index.html"
            data-testid="download-link"
          >
            Download <span className="mono">index.html</span>
          </a>
        </div>

        <div className="panel">
          <div className="panel-title">Removed</div>
          <ul>
            {removed.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>

        <div className="panel warn">
          <div className="panel-title">Heads up</div>
          <p>
            This launcher fetches its game catalog + each game's HTML from{" "}
            <span className="mono">cdn.jsdelivr.net</span> at runtime. Without
            internet you will see <em>“Loading the library…”</em> then a
            connection error. That is the app's own design, not the ad layer —
            removing ads did not cause it. Full details are in the HTML
            comment at the top of the cleaned file.
          </p>
        </div>

        <div className="foot mono">
          31.2 KB · 554 lines · SHA-256 4b603098ea7e853c2f6c7026ad6032cfd37b3d692799f7f5f1e52c6d06d91367
        </div>
      </div>
    </div>
  );
}

export default App;
