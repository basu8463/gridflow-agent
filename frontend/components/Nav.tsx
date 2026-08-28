"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "New application" },
  { href: "/queue", label: "Review queue" },
  { href: "/rules", label: "Rulebooks" },
  { href: "/evals", label: "Evals" },
];

export function Nav() {
  const path = usePathname();
  return (
    <header className="border-b border-line bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="text-lg font-semibold tracking-tight text-navy">
            GridFlow
          </span>
          <span className="hidden text-xs uppercase tracking-[0.18em] text-muted sm:inline">
            Grid connection agent
          </span>
        </Link>
        <nav className="flex gap-1 text-sm">
          {LINKS.map((l) => {
            const active = path === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-full px-3 py-1.5 ${
                  active
                    ? "bg-navy text-white"
                    : "text-muted hover:bg-sand hover:text-ink"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
