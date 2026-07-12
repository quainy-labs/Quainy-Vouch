import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { SourceDetail } from "../types";

export function useSourceDetail(selectedSourceId: string | null) {
  const [sourceDetail, setSourceDetail] = useState<SourceDetail | null>(null);

  useEffect(() => {
    if (!selectedSourceId) {
      setSourceDetail(null);
      return;
    }
    api<SourceDetail>(`/sources/${selectedSourceId}`).then(setSourceDetail);
  }, [selectedSourceId]);

  return { sourceDetail, setSourceDetail };
}
