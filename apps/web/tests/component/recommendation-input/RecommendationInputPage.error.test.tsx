import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  RUN_ERROR_BACK_LABEL,
  RUN_ERROR_FALLBACK_MESSAGE,
  RUN_ERROR_PAGE_TITLE,
  RUN_ERROR_RETRY_LABEL,
} from "@/features/recommendation-input/constants";
import { RecommendationInputPage } from "@/features/recommendation-input/RecommendationInputPage";

const pushMock = vi.fn();
const useSearchParamsMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => useSearchParamsMock(),
}));

vi.mock("@/lib/api", () => ({
  fetchRelationshipMasters: vi.fn(),
  fetchOccasionMasters: vi.fn(),
  fetchSemanticConfigMasters: vi.fn(),
  fetchFeatureRuleMasters: vi.fn(),
  postRecommendationRun: vi.fn(),
}));

import {
  fetchFeatureRuleMasters,
  fetchOccasionMasters,
  fetchRelationshipMasters,
  fetchSemanticConfigMasters,
  postRecommendationRun,
} from "@/lib/api";

const mockedRelationships = vi.mocked(fetchRelationshipMasters);
const mockedOccasions = vi.mocked(fetchOccasionMasters);
const mockedSemantic = vi.mocked(fetchSemanticConfigMasters);
const mockedFeatureRules = vi.mocked(fetchFeatureRuleMasters);
const mockedPostRun = vi.mocked(postRecommendationRun);

function successEnvelope<T>(data: T) {
  return {
    status: 200 as const,
    headers: new Headers(),
    data: {
      data,
      meta: {
        requestId: "req-1",
        traceId: "trace-masters",
        generatedAt: "2026-07-16T00:00:00Z",
      },
    },
  };
}

function mockMastersSuccess() {
  mockedRelationships.mockResolvedValue(
    successEnvelope({
      relationships: [
        {
          relationshipCode: "friend",
          relationshipLabel: "友人",
          displayOrder: 1,
        },
      ],
    }) as never,
  );
  mockedOccasions.mockResolvedValue(
    successEnvelope({
      occasions: [
        { occasionCode: "thanks", occasionLabel: "お礼", displayOrder: 1 },
      ],
    }) as never,
  );
  mockedSemantic.mockResolvedValue(
    successEnvelope({
      configName: "default",
      versionLabel: "v1",
      semanticConcepts: [],
      featureDefinitions: [],
    }) as never,
  );
  mockedFeatureRules.mockResolvedValue(
    successEnvelope({
      configName: "default",
      versionLabel: "v1",
      baseValueRules: [],
      conceptFeatureRules: [],
    }) as never,
  );
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(screen.getByLabelText(/贈る相手/), "friend");
  await user.selectOptions(screen.getByLabelText(/用途/), "thanks");
  await user.type(screen.getByLabelText(/予算上限/), "5000");
}

describe("RecommendationInputPage error path (SCR-008)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    useSearchParamsMock.mockReturnValue(new URLSearchParams());
    mockMastersSuccess();
  });

  afterEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it("shows SCR-008 when postRecommendationRun returns API error", async () => {
    const user = userEvent.setup();
    mockedPostRun.mockResolvedValue({
      status: 422,
      headers: new Headers(),
      data: {
        error: {
          code: "GRS-REQ-001",
          message: "条件を確認してください。",
        },
        meta: {
          requestId: "req-run-1",
          traceId: "trace-run-err",
          generatedAt: "2026-07-16T00:00:00Z",
        },
      },
    } as never);

    render(<RecommendationInputPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "レコメンド条件入力" }),
      ).toBeInTheDocument();
    });

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "レコメンドを実行" }));

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: RUN_ERROR_PAGE_TITLE }),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("条件を確認してください。")).toBeInTheDocument();
    expect(screen.getByText("code: GRS-REQ-001")).toBeInTheDocument();
    expect(screen.getByText("traceId: trace-run-err")).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("shows fallback message when postRecommendationRun throws", async () => {
    const user = userEvent.setup();
    mockedPostRun.mockRejectedValue(new Error("network down"));

    render(<RecommendationInputPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "レコメンド条件入力" }),
      ).toBeInTheDocument();
    });

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "レコメンドを実行" }));

    await waitFor(() => {
      expect(screen.getByText(RUN_ERROR_FALLBACK_MESSAGE)).toBeInTheDocument();
    });
    expect(screen.queryByText(/code:/)).not.toBeInTheDocument();
  });

  it("returns to form when user clicks back from SCR-008", async () => {
    const user = userEvent.setup();
    mockedPostRun.mockResolvedValue({
      status: 500,
      headers: new Headers(),
      data: {
        error: { code: "GRS-SYS-001", message: "一時的な障害です。" },
        meta: {
          requestId: "req-run-2",
          traceId: "trace-back",
          generatedAt: "2026-07-16T00:00:00Z",
        },
      },
    } as never);

    render(<RecommendationInputPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "レコメンド条件入力" }),
      ).toBeInTheDocument();
    });

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "レコメンドを実行" }));

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: RUN_ERROR_PAGE_TITLE }),
      ).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("button", { name: RUN_ERROR_BACK_LABEL }),
    );

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "レコメンド条件入力" }),
      ).toBeInTheDocument();
    });
    expect(screen.queryByText("一時的な障害です。")).not.toBeInTheDocument();
  });

  it("re-runs recommendation when user clicks retry from SCR-008", async () => {
    const user = userEvent.setup();
    mockedPostRun
      .mockResolvedValueOnce({
        status: 422,
        headers: new Headers(),
        data: {
          error: { code: "GRS-REQ-001", message: "再試行してください。" },
          meta: {
            requestId: "req-run-3",
            traceId: "trace-retry",
            generatedAt: "2026-07-16T00:00:00Z",
          },
        },
      } as never)
      .mockResolvedValueOnce({
        status: 422,
        headers: new Headers(),
        data: {
          error: { code: "GRS-REQ-001", message: "再試行してください。" },
          meta: {
            requestId: "req-run-4",
            traceId: "trace-retry-2",
            generatedAt: "2026-07-16T00:00:00Z",
          },
        },
      } as never);

    render(<RecommendationInputPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "レコメンド条件入力" }),
      ).toBeInTheDocument();
    });

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "レコメンドを実行" }));

    await waitFor(() => {
      expect(screen.getByText("再試行してください。")).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("button", { name: RUN_ERROR_RETRY_LABEL }),
    );

    await waitFor(() => {
      expect(mockedPostRun).toHaveBeenCalledTimes(2);
    });
    expect(screen.getByText("traceId: trace-retry-2")).toBeInTheDocument();
  });
});
