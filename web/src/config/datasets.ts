export interface Dataset {
  id: string;
  name: string;
  filename: string;
  description?: string;
  dateRange: {
    minDate: string; // Format ISO: YYYY-MM-DD
    maxDate: string; // Format ISO: YYYY-MM-DD
  };
}

export const AVAILABLE_DATASETS: Dataset[] = [
  {
    id: "aapl",
    name: "Apple",
    filename: "AAPL.csv",
    description: "Apple Inc. stock data",
    dateRange: {
      minDate: "2020-01-02",
      maxDate: "2024-12-31"
    }
  },
  {
    id: "amzn",
    name: "Amazon",
    filename: "AMZN.csv",
    description: "Amazon.com Inc. stock data",
    dateRange: {
      minDate: "2020-01-02",
      maxDate: "2024-12-31"
    }
  },
  {
    id: "fb",
    name: "Meta",
    filename: "FB.csv",
    description: "Meta Platforms Inc. stock data",
    dateRange: {
      minDate: "2020-01-02",
      maxDate: "2024-12-31"
    }
  },
  {
    id: "googl",
    name: "Alphabet",
    filename: "GOOGL.csv",
    description: "Alphabet Inc. stock data",
    dateRange: {
      minDate: "2020-01-02",
      maxDate: "2024-12-31"
    }
  },
  {
    id: "msft",
    name: "Microsoft",
    filename: "MSFT.csv",
    description: "Microsoft Corp. stock data",
    dateRange: {
      minDate: "2020-01-02",
      maxDate: "2024-12-31"
    }
  },
  {
    id: "nflx",
    name: "Netflix",
    filename: "NFLX.csv",
    description: "Netflix Inc. stock data",
    dateRange: {
      minDate: "2020-01-02",
      maxDate: "2024-12-31"
    }
  },
  {
    id: "nvda",
    name: "NVIDIA",
    filename: "NVDA.csv",
    description: "NVIDIA Corp. stock data",
    dateRange: {
      minDate: "2020-01-02",
      maxDate: "2024-12-31"
    }
  },
];

export async function fetchDatasetFile(filename: string): Promise<File> {
  const response = await fetch(`/data/datasets/${filename}`);
  if (!response.ok) {
    throw new Error(
      `Failed to fetch dataset ${filename}: ${response.statusText}`,
    );
  }

  const blob = await response.blob();
  return new File([blob], filename, { type: "text/csv" });
}

export function getDatasetById(id: string): Dataset | undefined {
  return AVAILABLE_DATASETS.find((dataset) => dataset.id === id);
}
