"use client";

import { useEffect, useState } from "react";

import { loadSupplyNameMap } from "@backoffice/reporting/lib/display-names";

export const useSupplyNames = (): Record<number, string> => {
  const [names, setNames] = useState<Record<number, string>>({});

  useEffect(() => {
    let active = true;
    void loadSupplyNameMap()
      .then((map) => {
        if (active) setNames(map);
      })
      .catch(() => {
        if (active) setNames({});
      });
    return () => {
      active = false;
    };
  }, []);

  return names;
};
