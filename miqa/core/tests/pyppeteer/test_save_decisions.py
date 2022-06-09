import pytest

from miqa.core.tasks import import_data


@pytest.mark.pyppeteer
async def test_save_decisions_tier_1(
    page,
    log_in,
    webpack_server,
    user,
    project_factory,
):
    project = project_factory(
        creator=user,
        name='Demo Project',
        import_path='samples/demo_project.csv',
    )
    project.update_group('tier_1_reviewer', [user])
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

    # Mark the second scan as questionable,
    # get a warning that there must be a comment or chip selection,
    # Then make a comment and try again
    await (
        await page.waitForXPath(
            '//span[contains(@class, "v-btn__content")][contains(.,"Questionable")]'
        )
    ).click()
    assert await page.waitForXPath(
        '//div[contains(@class,"red--text")]'
        '[contains(.," must have a comment or artifact selection")]'
    )
    await (await page.waitForXPath('//textarea[contains(@name, "input-comment")]')).type(
        'This is my comment for this questionable scan.'
    )
    await (
        await page.waitForXPath(
            '//span[contains(@class, "v-btn__content")][contains(.,"Questionable")]'
        )
    ).click()
    await page.waitFor(1_000)

    # Mark all artifacts as present on the third scan and mark it as questionable
    artifact_chips = await page.xpath('//span[contains(@class,"v-chip__content")]')
    [(await chip.click()) for chip in artifact_chips]
    await (
        await page.waitForXPath(
            '//span[contains(@class, "v-btn__content")][contains(.,"Questionable")]'
        )
    ).click()
    await page.waitFor(1_000)

    # Go back up a scan and confirm the previous decision marked all artifacts as present
    await (await page.waitForXPath('//i[contains(@class, "fa-caret-up")]')).click()
    saved_artifacts = await page.xpath(
        '//div[contains(., "No comment")]/following-sibling::div/'
        'span/span[contains(@class,"v-chip__content")]'
    )
    assert len(saved_artifacts) == len(artifact_chips)

    # Submit another decision on the third scan
    # This time marking all artifacts as absent and the scan as Usable
    artifact_chips = await page.xpath('//span[contains(@class,"v-chip__content")]')
    [(await chip.click()) for chip in artifact_chips]
    [(await chip.click()) for chip in artifact_chips]
    await (await page.waitForXPath('//textarea[contains(@name, "input-comment")]')).type(
        'I disagree.'
    )
    await (
        await page.waitForXPath('//span[contains(@class, "v-btn__content")][contains(.,"Usable")]')
    ).click()
    await page.waitFor(1_000)

    # Go back up a scan and confirm the previous decision marked all artifacts as absent
    await (await page.waitForXPath('//i[contains(@class, "fa-caret-up")]')).click()
    saved_artifacts = await page.xpath(
        '//div[contains(., "I disagree")]/following-sibling::div/'
        'span/span[contains(@class,"v-chip__content")]'
    )
    assert len(saved_artifacts) == 0

    # Go back to the project page
    await (await page.waitForXPath('//a[contains(., "Projects")]')).click()
    await (
        await page.waitForXPath(f'//div[contains(@class, "col")][contains(.,"{project.name}")]')
    ).click()
    await page.waitFor(3_000)

    # confirm that the number of scans awaiting tier 2 review is 3
    assert await (page.waitForXPath('//span[contains(., "needs tier 2 review (3)")]'))


@pytest.mark.pyppeteer
async def test_save_decisions_tier_2(
    page,
    log_in,
    webpack_server,
    user,
    project_factory,
):
    project = project_factory(
        creator=user,
        name='Demo Project',
        import_path='samples/demo_project.csv',
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

    # Mark the second scan as unusable,
    # get a warning that there must be a comment or chip selection,
    # Then make a comment and try again
    await (
        await page.waitForXPath(
            '//span[contains(@class, "v-btn__content")][contains(.,"Unusable")]'
        )
    ).click()
    assert await page.waitForXPath(
        '//div[contains(@class,"red--text")]'
        '[contains(.," must have a comment or artifact selection")]'
    )
    await (await page.waitForXPath('//textarea[contains(@name, "input-comment")]')).type(
        'This is my comment for this unusable scan.'
    )
    await (
        await page.waitForXPath(
            '//span[contains(@class, "v-btn__content")][contains(.,"Unusable")]'
        )
    ).click()
    await page.waitFor(1_000)

    # Mark all artifacts as present on the third scan and mark it as usable-extra
    artifact_chips = await page.xpath('//span[contains(@class,"v-chip__content")]')
    [(await chip.click()) for chip in artifact_chips]
    await (
        await page.waitForXPath(
            '//span[contains(@class, "v-btn__content")][contains(.,"Usable-Extra")]'
        )
    ).click()
    await page.waitFor(1_000)

    # Go back to the project page
    await (await page.waitForXPath('//a[contains(., "Projects")]')).click()
    await (
        await page.waitForXPath(f'//div[contains(@class, "col")][contains(.,"{project.name}")]')
    ).click()
    await page.waitFor(3_000)

    # confirm that the number of complete scans is 3
    assert await (page.waitForXPath('//span[contains(., "complete (3)")]'))
