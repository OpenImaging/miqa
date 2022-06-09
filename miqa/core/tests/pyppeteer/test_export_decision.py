import pandas
import pytest

from miqa.core.tasks import import_data


@pytest.mark.pyppeteer
async def test_export_project_with_decisions(
    page,
    log_in,
    webpack_server,
    user,
    project_factory,
):
    export_path = 'samples/demo_project_export.csv'
    project = project_factory(
        creator=user,
        name='Demo Project',
        import_path='samples/demo_project.csv',
        export_path=export_path,
    )
    project.update_group('tier_2_reviewer', [user])
    import_data(project_id=project.id)
    await log_in(user)

    # Open the first scan
    await (
        await page.waitForXPath(f'//div[contains(@class, "col")][contains(.,"{project.name}")]')
    ).click()
    await page.waitFor(1_000)
    assert await page.waitForXPath('//div[contains(.,"IXI002")]')
    scans = await page.xpath('//ul[contains(@class, "scans")]/li')
    await scans[0].click()
    await page.waitFor(1_000)

    # Mark the first scan as Usable
    await (
        await page.waitForXPath('//span[contains(@class, "v-btn__content")][contains(.,"Usable")]')
    ).click()
    await page.waitFor(1_000)

    # Mark the second scan as unusable
    await (await page.waitForXPath('//textarea[contains(@name, "input-comment")]')).type(
        'This is my comment for this unusable scan.'
    )
    await (
        await page.waitForXPath(
            '//span[contains(@class, "v-btn__content")][contains(.,"Unusable")]'
        )
    ).click()
    await page.waitFor(1_000)

    # Go back to the project page
    await (await page.waitForXPath('//a[contains(., "Projects")]')).click()
    await (
        await page.waitForXPath(f'//div[contains(@class, "col")][contains(.,"{project.name}")]')
    ).click()
    await page.waitFor(1_000)

    # perform the export
    await (await page.waitForXPath('//button[span[.=" Export "]]')).click()
    await page.waitFor(4_000)

    # read the export file
    export_df = pandas.read_csv(export_path)
    ixi002 = export_df.groupby('experiment_name').get_group('IXI002')
    ixi002_scans = ixi002.groupby('scan_name')
    first_scan_row = ixi002_scans.get_group('0828-DTI').iloc[0].fillna('')
    second_scan_row = ixi002_scans.get_group('0828-MRA').iloc[0].fillna('')

    assert first_scan_row['last_decision'] == 'U'
    assert first_scan_row['last_decision_creator'] == user.email
    assert first_scan_row['last_decision_note'] == ''

    assert second_scan_row['last_decision'] == 'UN'
    assert second_scan_row['last_decision_creator'] == user.email
    assert second_scan_row['last_decision_note'] == 'This is my comment for this unusable scan.'
