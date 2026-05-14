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
    <header className="w-full border-b border-b7-green-border bg-black">
      <div className="overflow-x-auto">
        <pre
          aria-label="BEST 7 DAYS MULA"
          className="text-b7-green text-xs sm:text-sm md:text-base leading-tight px-4 py-3 whitespace-pre"
        >
          {ART}
        </pre>
      </div>
    </header>
  );
}
