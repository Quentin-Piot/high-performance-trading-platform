export interface Dataset {
  id: string;
  name: string;
  filename: string;
  description?: string;
}

export const AVAILABLE_DATASETS: Dataset[] = [
  {
    id: "aapl",
    name: "Apple",
    filename: "AAPL.csv",
    description: "Apple Inc. stock data",
  },
  {
    id: "amzn",
    name: "Amazon",
    filename: "AMZN.csv",
    description: "Amazon.com Inc. stock data",
  },
  {
    id: "fb",
    name: "Meta",
    filename: "FB.csv",
    description: "Meta Platforms Inc. stock data",
  },
  {
    id: "googl",
    name: "Alphabet",
    filename: "GOOGL.csv",
    description: "Alphabet Inc. stock data",
  },
  {
    id: "msft",
    name: "Microsoft",
    filename: "MSFT.csv",
    description: "Microsoft Corp. stock data",
  },
  {
    id: "nflx",
    name: "Netflix",
    filename: "NFLX.csv",
    description: "Netflix Inc. stock data",
  },
  {
    id: "nvda",
    name: "NVIDIA",
    filename: "NVDA.csv",
    description: "NVIDIA Corp. stock data",
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
