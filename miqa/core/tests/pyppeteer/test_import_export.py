import pytest


async def get_current_num_scans(page):
    return len(await page.xpath('//ul[contains(@class, "scans")]/li'))


async def edit_import_export_paths(page, import_path, export_path):
    # Edit import path
    import_path_input = await page.waitForXPath('//input[contains(@name, "import-path")]')
    await import_path_input.click({'clickCount': 3})  # highlight the text to overwrite it
    await import_path_input.type(import_path)
    await page.waitFor(1_000)

    # Edit export path
    import_path_input = await page.waitForXPath('//input[contains(@name, "export-path")]')
    await import_path_input.click({'clickCount': 3})  # highlight the text to overwrite it
    await import_path_input.type(export_path)
    await page.waitFor(1_000)

    # Click save
    save_button = await page.waitForXPath('//button[span[.=" Save "]][@type="submit"]')
    await save_button.click()
    await page.waitFor(1_000)
    # If save was successful, the save button will be disabled.
    assert await page.evaluate('(element) => element.disabled', save_button)


async def perform_import(page):
    # Click import button, and again in the modal confirmation
    await (await page.waitForXPath('//button[span[.=" Import "]]')).click()
    await page.waitFor(1_000)
    await (
        await page.waitForXPath(
            '//div[contains(@class, "v-card__actions")]//button[span[.=" Import "]]'
        )
    ).click()
    await page.waitFor(6_000)
    await page.waitForXPath('//div[@class="v-snack__content"][contains(., "Import finished")]')
    # Wait for the snackbar message to go away
    await page.waitFor(5_000)


async def perform_export(page):
    # Click export button
    await (await page.waitForXPath('//button[span[.=" Export "]]')).click()
    await page.waitFor(2_000)
    await page.waitForXPath(
        '//div[@class="v-snack__content"][contains(., "Saved data to file successfully")]'
    )
    # Wait for the snackbar message to go away
    await page.waitFor(5_000)


@pytest.mark.pyppeteer
async def test_project_import_export(
    page,
    log_in,
    webpack_server,
    user_factory,
    project_factory,
):
    creator = user_factory()
    project = project_factory(creator=creator, name='Demo Project')
    project.update_group('tier_2_reviewer', [creator])

    await log_in(creator)
    # Click on the project in the project selector
    await (
        await page.waitForXPath(f'//div[contains(@class, "col")][contains(.,"{project.name}")]')
    ).click()
    await page.waitFor(1_000)

    # Assert no scans yet
    assert (await get_current_num_scans(page)) == 0

    await edit_import_export_paths(
        page,
        import_path='samples/demo_project.csv',
        export_path='samples/demo_project_export.csv',
    )
    await perform_import(page)
    await perform_export(page)

    # Assert number of imported scans
    assert (await get_current_num_scans(page)) == 9


@pytest.mark.pyppeteer
async def test_global_import_export(
    page,
    log_in,
    webpack_server,
    user_factory,
    project_factory,
):
    admin = user_factory(is_superuser=True)
    project_factory(name='Demo Project')  # make sure demo project exists

    await log_in(admin)
    # Click on Global import/export button
    await (await page.waitForXPath('//button[span[.=" Global import/export "]]')).click()
    await page.waitFor(1_000)

    await edit_import_export_paths(
        page,
        import_path='samples/demo_project.csv',
        export_path='samples/demo_project_export.csv',
    )
    await perform_import(page)
    await perform_export(page)
