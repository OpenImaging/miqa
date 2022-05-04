from guardian.shortcuts import get_perms
import pytest


async def get_collaborators(page):
    """Return the list of collaborator emails."""
    rows = await page.xpath(
        '//div[contains(.,"Collaborators")]'
        '/../following-sibling::div/div[contains(@class, "v-avatar")]'
    )
    return [(await page.evaluate('(element) => element.textContent', row)).strip() for row in rows]


async def get_tier_1_reviewers(page):
    """Return the list of tier 1 reviewer emails."""
    rows = await page.xpath(
        '//div[contains(.,"Members")]'
        '/../following-sibling::div[span[contains(., "tier 1 reviewer")]]'
    )
    return [
        (await page.evaluate('(element) => element.textContent', row)).strip().split(' ')[0]
        for row in rows
    ]


async def get_tier_2_reviewers(page):
    """Return the list of tier 2 reviewer emails."""
    rows = await page.xpath(
        '//div[contains(.,"Members")]'
        '/../following-sibling::div[span[contains(., "tier 2 reviewer")]]'
    )
    return [
        (await page.evaluate('(element) => element.textContent', row)).strip().split(' ')[0]
        for row in rows
    ]


@pytest.mark.pyppeteer
async def test_change_project_ownership(page, log_in, webpack_server, user_factory, project):
    admin = user_factory(is_superuser=True)
    collaborator = user_factory()
    tier_1_user = user_factory()
    tier_2_user = user_factory()

    await log_in(admin)
    # Click on the project in the project selector
    await (
        await page.waitForXPath(f'//div[contains(@class, "col")][contains(.,"{project.name}")]')
    ).click()
    # Wait for the project settings page to load
    await page.waitFor(1_000)
    # Assert that no one associated with the project yet
    assert await get_collaborators(page) == []
    assert await get_tier_1_reviewers(page) == []
    assert await get_tier_2_reviewers(page) == []

    # Assign the Tier 1 and Tier 2 reviewers
    # Open the Members modal
    await (
        await page.waitForXPath('//div[@class="col col-12"][contains(., "Members")]/button')
    ).click()
    # Open the Tier 1 reviewers selection menu
    tier_1_input = await page.waitForXPath(
        '//div[label="Select Tier 1 Reviewers"]/div[@class="v-select__selections"]/input'
    )
    await tier_1_input.click()
    await page.waitFor(500)
    # Select the Tier 1 reviewer
    await (
        await page.waitForXPath(
            f'//div[@class="v-list-item__title"]'
            f'[.="{tier_1_user.first_name + " " + tier_1_user.last_name}"]'
        )
    ).click()
    # Close the selection menu
    await tier_1_input.press('Escape')
    await page.waitFor(500)
    # Open the Tier 2 reviewers selection menu
    tier_2_input = await page.waitForXPath(
        '//div[label="Select Tier 2 Reviewers"]/div[@class="v-select__selections"]/input'
    )
    await tier_2_input.click()
    await page.waitFor(500)
    # Select the Tier 2 reviewer
    await (
        await page.waitForXPath(
            f'(//div[@class="v-list-item__title"]'
            f'[.="{tier_2_user.first_name + " " + tier_2_user.last_name}"])[2]'
        )
    ).click()
    # Close the selection menu
    await tier_2_input.press('Escape')
    await page.waitFor(500)
    # Save changes
    await (await page.waitForXPath('//button[contains(., "Save changes")]')).click()
    await page.waitFor(500)

    # Assign the collaborator
    # Open the Collaborators modal
    await (
        await page.waitForXPath('//div[@class="col col-12"][contains(., "Collaborators")]/button')
    ).click()
    # Open the Collaborators selection menu
    collaborators_input = await page.waitForXPath(
        '//div[label="Select Collaborators"]/div[@class="v-select__selections"]/input'
    )
    await collaborators_input.click()
    await page.waitFor(500)
    # Select the Tier 2 reviewer
    await (
        await page.waitForXPath(
            f'//div[@class="v-list-item__title"]'
            f'[.="{collaborator.first_name + " " + collaborator.last_name}"]'
        )
    ).click()
    # Close the selection menu
    await collaborators_input.press('Escape')
    await page.waitFor(500)
    # Save changes
    await (await page.waitForXPath('//button[contains(., "Save changes")]')).click()
    await page.waitFor(500)

    # Verify that all users have the correct roles on the project
    assert await get_collaborators(page) == [collaborator.first_name[0] + collaborator.last_name[0]]
    assert await get_tier_1_reviewers(page) == [
        tier_1_user.first_name[0] + tier_1_user.last_name[0]
    ]
    assert await get_tier_2_reviewers(page) == [
        tier_2_user.first_name[0] + tier_2_user.last_name[0]
    ]
    assert get_perms(collaborator, project) == ['collaborator']
    assert get_perms(tier_1_user, project) == ['tier_1_reviewer']
    assert get_perms(tier_2_user, project) == ['tier_2_reviewer']
