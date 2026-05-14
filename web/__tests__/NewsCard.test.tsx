import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { NewsCard } from "@/components/NewsCard";

describe("NewsCard", () => {
  it("renders title (linked, opens new tab), publisher, and relative time", () => {
    const past = new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString();
    render(
      <NewsCard
        item={{
          title: "Markets rally on AI optimism",
          publisher: "Reuters",
          link: "https://example.com/article",
          published_at: past,
        }}
      />,
    );

    const link = screen.getByRole("link", {
      name: /markets rally on ai optimism/i,
    });
    expect(link).toHaveAttribute("href", "https://example.com/article");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");

    expect(screen.getByText(/reuters/i)).toBeInTheDocument();
    expect(screen.getByText(/ago/i)).toBeInTheDocument();
  });

  it("renders thumbnail when provided", () => {
    render(
      <NewsCard
        item={{
          title: "T",
          publisher: "P",
          link: "https://x.example",
          published_at: new Date().toISOString(),
          thumbnail: "https://img.example/x.png",
        }}
      />,
    );
    const img = document.querySelector("img");
    expect(img).not.toBeNull();
    expect(img?.getAttribute("src")).toBe("https://img.example/x.png");
  });
});
