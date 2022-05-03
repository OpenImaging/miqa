from django.core import mail
from guardian.shortcuts import assign_perm
import pytest


@pytest.mark.pyppeteer
async def test_send_email(page, log_in, user, samples_project):
    assign_perm('tier_1_reviewer', user, samples_project)

    experiment = samples_project.experiments.first()
    scan = experiment.scans.first()

    await log_in(user)
    # Click on the project in the project selector
    await (
        await page.waitForXPath(
            f'//div[contains(@class, "col")][contains(.,"{samples_project.name}")]'
        )
    ).click()
    # Wait a second for the project page to open
    await page.waitFor(1_000)
    # Click on the name of the scan to navigate to the scan view
    await (await page.waitForXPath(f'//a/span[.=" {scan.name} "]')).click()
    # Wait a second for the scan page to open
    await page.waitFor(1_000)
    # Click on the email icon to open the email modal
    await (await page.waitForXPath('//button//i[.="email"]')).click()
    # Wait a second for the modal to open
    await page.waitFor(1_000)
    # Ensure that the default email recipient is present in the To field
    await page.waitForXPath(
        f'//div[label[.="to"]]/div[@class="v-select__selections"]'
        f'/span[.=" {samples_project.default_email_recipients} "]'
    )
    # Ensure that the current user is present in the CC field
    await page.waitForXPath(
        f'//div[label[.="cc"]]/div[@class="v-select__selections"]'
        f'/span[.=" {user.email} "]//button'
    )
    # Add a user in the To field
    await (await page.waitForXPath('//div[label[.="to"]]/div/input')).type('foo_bar@kitware.com')
    # Click on a different field so that the new recipient chip saves
    await (await page.waitForXPath('//div[label[.="Subject"]]/input')).click()
    # Add some exclamation marks to the subject
    await (await page.waitForXPath('//div[label[.="Subject"]]/input')).type('!!!')
    # Add a sign off to the body
    await (await page.waitForXPath('//div[label[.="Body"]]/textarea')).type('Regards\n')
    # Click send
    await (await page.waitForXPath('//button[span[.=" Send "]]')).click()
    # Wait a second for the email to send
    await page.waitFor(1_000)

    # Test that the email was sent as expected
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == [samples_project.default_email_recipients, 'foo_bar@kitware.com']
    assert email.cc == [user.email]
    assert email.subject == f'Regarding {samples_project.name}, {experiment.name}, {scan.name}!!!'
    assert email.body == f'Experiment: {experiment.name}\nScan: {scan.name}\nRegards\n'


@pytest.mark.pyppeteer
async def test_send_email_screenshot(page, log_in, user, samples_project):
    assign_perm('tier_1_reviewer', user, samples_project)

    experiment = samples_project.experiments.first()
    scan = experiment.scans.first()

    await log_in(user)
    # Click on the project in the project selector
    await (
        await page.waitForXPath(
            f'//div[contains(@class, "col")][contains(.,"{samples_project.name}")]'
        )
    ).click()
    # Wait a second for the project page to open
    await page.waitFor(1_000)
    # Click on the name of the scan to navigate to the scan view
    await (await page.waitForXPath(f'//a/span[.=" {scan.name} "]')).click()
    # Wait a second for the scan page to open
    await page.waitFor(1_000)

    # Take a screenshot of each render
    await (await page.waitForXPath('(//button//i[.="add_a_photo"])[1]')).click()
    await page.waitFor(1_000)
    await (await page.waitForXPath('//button[.=" Attach to email draft "]')).click()
    await page.waitFor(1_000)
    await (await page.waitForXPath('(//button//i[.="add_a_photo"])[2]')).click()
    await page.waitFor(1_000)
    await (await page.waitForXPath('//button[.=" Attach to email draft "]')).click()
    await page.waitFor(1_000)
    await (await page.waitForXPath('(//button//i[.="add_a_photo"])[3]')).click()
    await page.waitFor(1_000)
    await (await page.waitForXPath('//button[.=" Attach to email draft "]')).click()
    await page.waitFor(1_000)

    # Click on the email icon to open the email modal
    await (await page.waitForXPath('//button//i[.="email"]')).click()
    # Wait a second for the modal to open
    await page.waitFor(1_000)
    # The screenshots are all attached by default, so no manual action necessary
    # Click send
    await (await page.waitForXPath('//button[span[.=" Send "]]')).click()
    # Wait a second for the email to send
    await page.waitFor(1_000)

    # Test that the email was sent as expected
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert len(email.attachments) == 3
