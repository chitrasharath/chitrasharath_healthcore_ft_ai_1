export const countryToJurisdiction = (country: string): "us" | "uk" =>
  country === "UK" ? "uk" : "us";
