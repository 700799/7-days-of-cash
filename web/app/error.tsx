"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <main className="min-h-screen bg-black text-b7-green p-8 font-mono">
      <h1 className="text-xl">{`> ERROR`}</h1>
      <p className="mt-4 text-b7-green-dim">{error.message}</p>
      <button
        type="button"
        onClick={reset}
        className="mt-6 px-3 py-1 border border-b7-green-border hover:bg-green-500/10 transition uppercase text-xs"
      >
        [ RETRY ]
      </button>
    </main>
  );
}
