/** Inline script to apply saved theme before paint (avoids flash). */
export const ThemeScript = () => (
  <script
    dangerouslySetInnerHTML={{
      __html: `(function(){try{var k='healthcore_theme';var p=localStorage.getItem(k)||'system';var dark=p==='dark'||(p==='system'&&window.matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.classList.toggle('dark',dark);}catch(e){}})();`,
    }}
  />
);
