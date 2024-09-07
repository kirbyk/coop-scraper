from datetime import datetime
from prefect import flow, task
from prefect.blocks.system import Secret
from zoneinfo import ZoneInfo
import httpx
import mechanicalsoup
import pymongo
import sys


browser = mechanicalsoup.StatefulBrowser()


def current_time_hourly():
    now = datetime.now(ZoneInfo("America/New_York"))
    return now.replace(minute=0, second=0, microsecond=0)


@task(log_prints=True)
def login(username, password):
    browser.open("https://members.foodcoop.com/services/login/")

    browser.select_form('form[action="/services/login/"]')
    browser["username"] = username
    browser["password"] = password
    resp = browser.submit_selected()

    if resp.url == "https://members.foodcoop.com/services/login/":
        raise Exception("Login failed")
    else:
        print("Login successful")


def logout():
    browser.open("https://members.foodcoop.com/services/logout/")


@task(log_prints=True)
def parse_shifts(shift_elements, shifts):
    for shift in shift_elements:
        time = shift.b.text
        shift.b.extract()
        type = shift.text.replace("🥕", "").strip()
        date = shift.parent.p.b.text.replace("\xa0", " ")

        shifts.append(
            {"date": date, "time": time, "type": type, "created": current_time_hourly()}
        )

    print(f"Processed {len(shift_elements)} shifts. Total shifts: {len(shifts)}")


@task(log_prints=True)
def connect_to_mongodb():
    try:
        mongodb_uri_block = Secret.load("mongodb-uri")
        client = pymongo.MongoClient(mongodb_uri_block.get())
        client.admin.command("ping")
        print("Successfully connected to MongoDB")
        return client
    except pymongo.errors.ConnectionFailure as e:
        print(f"Failed to connect to MongoDB: {e}", file=sys.stderr)
        sys.exit(1)


@task(log_prints=True)
def save_shifts(shifts, client):
    shift_collection = client["coop"]["shifts"]

    try:
        result = shift_collection.insert_many(shifts)
        print(f"Successfully inserted {len(result.inserted_ids)} documents")
    except pymongo.errors.BulkWriteError as e:
        print(f"Error inserting documents: {e}", file=sys.stderr)
        sys.exit(1)


@flow(name="Coop Shift Scraper", log_prints=True)
def get_shifts():
    username_block = Secret.load("coop-username")
    password_block = Secret.load("coop-password")
    logout()
    login(username_block.get(), password_block.get())

    shifts = []
    browser.open("https://members.foodcoop.com/services/shifts/")

    while True:
        page = browser.get_current_page()
        shift_elements = page.find_all(class_="shift")
        parse_shifts(shift_elements, shifts)

        try:
            browser.follow_link(text="Next Week →")
        except mechanicalsoup.LinkNotFoundError:
            print("No more weeks to process.")
            break

    print(f"Total shifts collected: {len(shifts)}")

    client = connect_to_mongodb()
    save_shifts(shifts, client)


if __name__ == "__main__":
    get_shifts()
