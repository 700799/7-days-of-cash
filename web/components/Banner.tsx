const ART = String.raw`
 ____  _____ ____ _____   _____   ____    _ __   _______
| __ )| ____/ ___|_   _| |___  | |  _ \  / \\ \ / / ____|
|  _ \|  _| \___ \ | |      / /  | | | |/ _ \\ V /|  _|
| |_) | |___ ___) || |     / /   | |_| / ___ \| | | |___
|____/|_____|____/ |_|    /_/    |____/_/   \_\_| |_____|
                  M  U  L  A
`;

export function Banner() {
  return (
    <header className="w-full border-b border-green-500/40 bg-black">
      <pre
        aria-label="BEST 7 DAYS MULA"
        className="text-green-400 text-[10px] sm:text-xs md:text-sm leading-tight px-4 py-3 overflow-x-auto whitespace-pre"
      >
        {ART}
      </pre>
    </header>
  );
}
