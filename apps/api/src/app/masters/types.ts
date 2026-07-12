/** occasion_master 行（DB / scaffold）。is_active はフィルタ専用。 */
export type OccasionMasterRow = {
  occasion_code: string;
  occasion_label: string;
  display_order: number;
  is_active?: boolean;
};

/** Public Response の Occasion 選択肢（契約・OpenAPI）。 */
export type OccasionMasterItem = {
  occasionCode: string;
  occasionLabel: string;
  displayOrder?: number;
};

export type OccasionMastersSuccessResponse = {
  data: {
    occasions: OccasionMasterItem[];
  };
  meta: {
    traceId: string;
    requestId: string;
    generatedAt: string;
    count: number;
  };
};
