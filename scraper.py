import mechanicalsoup
from prefect import flow, task
from prefect.blocks.system import Secret
import httpx


browser = mechanicalsoup.StatefulBrowser()


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

        shifts.append({"date": date, "time": time, "type": type})

    print(f"Processed {len(shift_elements)} shifts. Total shifts: {len(shifts)}")


@flow(name="Coop Shift Scraper", log_prints=True)
def get_shifts():
    username_block = Secret.load("coop-username")
    password_block = Secret.load("coop-password")
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


if __name__ == "__main__":
    get_shifts()
