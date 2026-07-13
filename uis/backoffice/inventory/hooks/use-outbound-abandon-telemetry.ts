"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

import {
  isOutboundDirty,
  trackOutboundAbandon,
  type OutboundFields,
} from "@backoffice/inventory/lib/outbound-abandon";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";

const OUTBOUND_PATH = "/inventory/orders/outbound";

const linkPathname = (href: string): string => {
  if (href.startsWith("http://") || href.startsWith("https://")) {
    try {
      return new URL(href).pathname;
    } catch {
      return href;
    }
  }
  return href.split("?")[0] ?? href;
};

const isLeavingOutboundLink = (href: string): boolean => {
  if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) {
    return false;
  }
  const path = linkPathname(href);
  return path !== OUTBOUND_PATH;
};

export const useOutboundAbandonTelemetry = (
  fields: OutboundFields,
  products: MedicalSupply[],
  submitted: boolean,
) => {
  const pathname = usePathname();
  const abandonEmittedRef = useRef(false);
  const fieldsRef = useRef(fields);
  const productsRef = useRef(products);
  const submittedRef = useRef(submitted);

  fieldsRef.current = fields;
  productsRef.current = products;
  submittedRef.current = submitted;

  useEffect(() => {
    const emit = (trigger: "navigation" | "tab_hidden") => {
      if (abandonEmittedRef.current || submittedRef.current) return;
      if (!isOutboundDirty(fieldsRef.current)) return;
      if (trackOutboundAbandon(fieldsRef.current, productsRef.current, trigger)) {
        abandonEmittedRef.current = true;
      }
    };

    const onLinkClick = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const anchor = target.closest("a[href]");
      if (!(anchor instanceof HTMLAnchorElement)) return;
      const href = anchor.getAttribute("href");
      if (!href || !isLeavingOutboundLink(href)) return;
      emit("navigation");
    };

    const onHidden = () => {
      if (document.visibilityState === "hidden") emit("tab_hidden");
    };

    const onPageHide = () => emit("navigation");

    document.addEventListener("click", onLinkClick, true);
    document.addEventListener("visibilitychange", onHidden);
    window.addEventListener("pagehide", onPageHide);
    return () => {
      document.removeEventListener("click", onLinkClick, true);
      document.removeEventListener("visibilitychange", onHidden);
      window.removeEventListener("pagehide", onPageHide);
      emit("navigation");
    };
  }, [pathname]);
};
