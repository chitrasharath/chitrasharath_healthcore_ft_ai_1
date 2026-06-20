export const TALENT_TRACKER_HOME = "/talent-tracker";

export const talentPath = (subpath: string): string => {
  const normalized = subpath.startsWith("/") ? subpath : `/${subpath}`;
  return `${TALENT_TRACKER_HOME}${normalized}`;
};
