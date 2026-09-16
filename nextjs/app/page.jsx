import InstallCommands from "./install-commands";

export default function Home() {
  return (
    <>
<a className="skip-link" href="#main">Skip to content</a>
  <header className="site-header shell">
    <a className="brand" href="#" aria-label="Digital Wellbeing Tracker home"><span className="brand-mark" aria-hidden="true">dw</span><span>digital wellbeing<span className="brand-caption">A little more intentional.</span></span></a>
    <nav aria-label="Main navigation"><a href="#features">Features</a><a href="#how-it-works">How it works</a><a className="nav-cta" href="https://github.com/DivyanshM30/digital-wellbeing-tracker">GitHub <span aria-hidden="true">↗</span></a></nav>
  </header>
  <main id="main">
    <section className="hero shell" aria-labelledby="hero-title">
      <div className="hero-copy">
        <p className="eyebrow"><span className="status-dot" aria-hidden="true"></span> BUILT FOR WINDOWS · STORED LOCALLY</p>
        <h1 id="hero-title">Less autopilot.<br />More <em>intention.</em></h1>
        <p className="hero-description">Your time deserves a little attention. See where it goes, set limits that work for you, and make room for life beyond the screen.</p>
        <div className="hero-actions"><a className="button button-dark" href="#get-started">Get started <span aria-hidden="true">↗</span></a><a className="text-link" href="#preview">Take a look <span aria-hidden="true">↓</span></a></div>
        <p className="hero-note">A Python desktop app. No account or API key needed.</p>
      </div>
      <div className="hero-art" aria-label="Illustration of balancing screen time and time away">
        <div className="orbit orbit-one"></div><div className="orbit orbit-two"></div>
        <span className="art-label">A LITTLE SPACE TO RECONNECT</span>
        <div className="balance-disc"><span className="disc-caption">BE PRESENT</span><span className="asterisk" aria-hidden="true">✳</span><span className="disc-bottom">one small habit at a time</span></div>
        <div className="floating-note"><span className="note-icon" aria-hidden="true">↗</span><div>A moment for yourself.<small>It starts with awareness.</small></div></div>
        <span className="art-bottom">YOUR SCREEN IS ONLY PART OF YOUR DAY.</span>
      </div>
    </section>
    <div className="principles shell" aria-label="Project highlights"><span><span aria-hidden="true">◉</span> Understand your habits</span><span><span aria-hidden="true">◷</span> Set your own boundaries</span><span><span aria-hidden="true">⌂</span> Keep your data on your device</span></div>
    <section className="section shell" id="features" aria-labelledby="features-title">
      <div className="section-heading"><p className="eyebrow">SMALL TOOLS. MEANINGFUL HABITS.</p><h2 id="features-title">Start by noticing.<br />Then find your balance.</h2><p>You don’t need another productivity score. You need a clearer picture of how you spend your time.</p></div>
      <div className="feature-grid">
        <article className="feature"><span className="feature-number">01 / AWARENESS</span><div className="mini-bars" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div><h3>See where the hours go.</h3><p>Track the foreground application and explore your usage in a simple dashboard, with time broken down by app.</p></article>
        <article className="feature"><span className="feature-number">02 / BOUNDARIES</span><div className="mini-clock" aria-hidden="true"><span></span></div><h3>A nudge when you need it.</h3><p>Choose application limits and warning thresholds. Voice reminders and desktop notifications help you notice when it’s time to pause.</p></article>
        <article className="feature"><span className="feature-number">03 / REFLECTION</span><div className="mini-trend" aria-hidden="true"><span>↗</span><i></i><i></i><i></i></div><h3>Get to know your patterns.</h3><p>Explore statistical usage summaries after recording at least three days. Use them as a starting point for reflection.</p></article>
      </div>
    </section>
    <section className="preview-section" id="preview" aria-labelledby="preview-title">
      <div className="shell">
        <div className="preview-heading"><div><p className="eyebrow">A CLOSER LOOK</p><h2 id="preview-title">Your habits, in view.</h2></div><p>A desktop dashboard for checking in.<br />Light and dark themes included.</p></div>
        <figure className="app-preview"><div className="window-bar"><span className="window-dot" aria-hidden="true"></span><span>Digital Wellbeing Tracker</span><span className="window-platform">WINDOWS DESKTOP</span></div><img src="landing_page/pic/overview-mock.png" alt="Overview with sample data: 3 hours 35 minutes across Code, Chrome, Figma and Spotify, with application usage bars and a limit check-in" width="1477" height="1065" loading="lazy" /><figcaption>Overview · Sample usage data for illustration. No personal activity shown.</figcaption></figure>
      </div>
    </section>
    <section className="section shell how-section" id="how-it-works" aria-labelledby="how-title"><div><p className="eyebrow">MAKE IT YOURS</p><h2 id="how-title">A gentler routine,<br />in three steps.</h2><p className="section-intro">Start small. The goal is to make your time feel more like your own.</p></div><ol className="steps"><li><span>01</span><div><h3>Start tracking</h3><p>Launch the Windows app and press Start Tracking to observe foreground application time.</p></div></li><li><span>02</span><div><h3>Choose your boundaries</h3><p>Add limits for the apps you want to be more intentional about. Choose your alert preferences in Settings.</p></div></li><li><span>03</span><div><h3>Check in and adjust</h3><p>Review your usage, notice your patterns, and adjust your limits to fit your day.</p></div></li></ol></section>
    <section className="start-section shell" id="get-started" aria-labelledby="start-title"><div className="start-copy"><p className="eyebrow">READY WHEN YOU ARE</p><h2 id="start-title">Make a little<br />room for yourself.</h2><p>Run the project from source on Windows with Python and Tcl/Tk installed.</p><a className="text-link" href="https://github.com/DivyanshM30/digital-wellbeing-tracker#readme">Read the setup guide <span aria-hidden="true">↗</span></a></div><InstallCommands /></section>
    <section className="project-notes shell" aria-labelledby="notes-title"><h2 id="notes-title">A few things to know</h2><details><summary>What does the tracker record?</summary><p>The app stores process names, window titles, and usage durations locally in plain-text files. Window titles can contain document or page names. The current version has no automatic retention controls.</p></details><details><summary>How accurate are the totals?</summary><p>This is a project in development. Idle time is currently included, daily rollover needs improvement, and repeated analysis can duplicate history. Treat the summaries as exploratory. See the <a href="https://github.com/DivyanshM30/digital-wellbeing-tracker/blob/main/IMPROVEMENTS.md">improvement review</a> for details.</p></details><details><summary>Will it close my applications?</summary><p>“Auto Shutdown Apps at Limit” defaults to enabled on a fresh setup and can close an application with unsaved work. Turn it off in Settings before tracking if you want reminders without termination.</p></details><details><summary>Does it support macOS or Linux?</summary><p>The current main.py implementation uses Windows APIs. macOS and Linux are not currently supported.</p></details></section>
  </main>
  <footer className="shell site-footer">
    <a className="brand" href="#"><span className="brand-mark" aria-hidden="true">dw</span><span>digital wellbeing</span></a>
    <p>Made with intention by Divyansh Mishra.</p>
    <nav className="footer-links" aria-label="Connect with Divyansh">
      <a href="https://www.linkedin.com/in/divyanshm30/" target="_blank" rel="noopener noreferrer">LinkedIn <span aria-hidden="true">↗</span></a>
      <a href="https://github.com/DivyanshM30" target="_blank" rel="noopener noreferrer">GitHub <span aria-hidden="true">↗</span></a>
      <a href="https://divyanshm.dev/" target="_blank" rel="noopener noreferrer">Portfolio <span aria-hidden="true">↗</span></a>
    </nav>
  </footer>
    </>
  );
}
