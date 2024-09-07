from prefect import flow

SOURCE_REPO = "https://github.com/kirbyk/coop-scraper.git"

if __name__ == "__main__":
    flow.from_source(
        source=SOURCE_REPO,
        entrypoint="scraper.py:get_shifts",
    ).deploy(
        name="coop-shift-scraper",
        work_pool_name="web-scraper",
        cron="0 * * * *",  # top of every hour
    )
