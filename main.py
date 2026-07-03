import argparse
import os

from scraper.faculty_scraper import main as run_scraper
from scraper.exporter import main as run_exporter

def main():
    parser = argparse.ArgumentParser(description="BOUN MIS Faculty Data Scraper and Exporter")
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip the scraping step and only run the exporter.",
    )
    parser.add_argument(
        "--lang",
        default="both",
        choices=["en", "tr", "both"],
        help="Language version to scrape/export.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between requests for the scraper.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of concurrent workers for scraping.",
    )
    args = parser.parse_args()

    # Create the outputs directory if it doesn't exist
    os.makedirs("outputs", exist_ok=True)

    if not args.skip_scrape:
        print("--- Running Scraper ---")
        # To pass arguments to the scraper's main function, we can temporarily modify sys.argv
        import sys
        original_argv = sys.argv
        sys.argv = [
            "scraper/faculty_scraper.py",
            "--lang",
            args.lang,
            "--delay",
            str(args.delay),
            "--workers",
            str(args.workers),
        ]
        run_scraper()
        sys.argv = original_argv
        print("--- Scraping Complete ---")
    else:
        print("--- Skipping Scraper ---")

    print("\n--- Running Exporter ---")
    # To pass arguments to the exporter's main function
    import sys
    original_argv = sys.argv
    sys.argv = ["scraper/exporter.py", "--lang", args.lang]
    run_exporter()
    sys.argv = original_argv
    print("--- Exporting Complete ---")


if __name__ == "__main__":
    main()
