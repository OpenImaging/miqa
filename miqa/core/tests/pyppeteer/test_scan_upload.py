# import pytest

from miqa.core.tests.pyppeteer.test_import_export import get_current_num_scans


# @pytest.mark.pyppeteer
async def test_upload_scans(
    page,
    log_in,
    webpack_server,
    user,
    project_factory,
):
    project = project_factory(creator=user, name='Demo Project')
    project.update_group('tier_2_reviewer', [user])
    await log_in(user)

    # Click on the project in the project selector
    await (
        await page.waitForXPath(f'//div[contains(@class, "col")][contains(.,"{project.name}")]')
    ).click()
    await page.waitFor(1_000)
    # Assert no scans yet
    assert (await get_current_num_scans(page)) == 0

    # Open upload modal
    await (
        await page.waitForXPath(
            '//span[contains(@class, "v-btn__content")][contains(.,"Add Scans")]'
        )
    ).click()
    assert await page.waitForXPath(
        '//div[contains(@class, "v-card__title")][contains(.,"Upload Image Files to Experiment")]'
    )

    new_experiment_input = await page.waitForXPath(
        '//label[contains(@class, "v-label")]'
        '[contains(.,"Name new Experiment")]/following::input[@type="text"]'
    )
    await new_experiment_input.type('Test Experiment')

    file_input = await page.waitForXPath(
        '//label[contains(@class, "v-label")]'
        '[contains(.,"Image files")]/following::input[@type="file"]'
    )

    await file_input.uploadFile(
        'samples/Demo Project/IXI002/0828-DTI/IXI002-Guys-0828-DTI-00.nii.gz',
        'samples/Demo Project/IXI002/0828-DTI/IXI002-Guys-0828-DTI-01.nii.gz',
        'samples/Demo Project/IXI002/0828-DTI/IXI002-Guys-0828-DTI-02.nii.gz',
    )
    await page.waitFor(3_000)
    await (
        await page.waitForXPath('//span[contains(@class, "v-btn__content")][contains(.,"Upload")]')
    ).click()
    await page.waitFor(5_000)

    # Assert there are 3 scans now, and that the experiment name appears as we typed it
    assert (await get_current_num_scans(page)) == 3
    assert await page.waitForXPath('//div[contains(.,"Test Experiment")]')

    scans = await page.xpath('//ul[contains(@class, "scans")]/li')
    await scans[0].click()

    assert await page.waitForXPath(
        '//div[contains(@class, "current-info-container")][contains(., "Demo Project")]'
        '/following::div/div[contains(., "Test Experiment")]'
    )
