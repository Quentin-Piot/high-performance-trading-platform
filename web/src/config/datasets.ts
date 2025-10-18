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
      minDate: "2014-09-29",
      maxDate: "2018-03-29"
    }
  },
  {
    id: "amzn",
    name: "Amazon",
    filename: "AMZN.csv",
    description: "Amazon.com Inc. stock data",
    dateRange: {
      minDate: "1997-05-15",
      maxDate: "2022-03-24"
    }
  },
  {
    id: "fb",
    name: "Meta",
    filename: "FB.csv",
    description: "Meta Platforms Inc. stock data",
    dateRange: {
      minDate: "2012-05-18",
      maxDate: "2022-03-24"
    }
  },
  {
    id: "googl",
    name: "Alphabet",
    filename: "GOOGL.csv",
    description: "Alphabet Inc. stock data",
    dateRange: {
      minDate: "2004-08-19",
      maxDate: "2022-03-24"
    }
  },
  {
    id: "msft",
    name: "Microsoft",
    filename: "MSFT.csv",
    description: "Microsoft Corp. stock data",
    dateRange: {
      minDate: "1986-03-13",
      maxDate: "2022-03-24"
    }
  },
  {
    id: "nflx",
    name: "Netflix",
    filename: "NFLX.csv",
    description: "Netflix Inc. stock data",
    dateRange: {
      minDate: "2002-05-23",
      maxDate: "2022-06-03"
    }
  },
  {
    id: "nvda",
    name: "NVIDIA",
    filename: "NVDA.csv",
    description: "NVIDIA Corp. stock data",
    dateRange: {
      minDate: "2019-05-23",
      maxDate: "2024-05-23"
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
