from app.integrations.apollo import ApolloClient


async def run_lead_discovery() -> dict:
    client = ApolloClient()
    payload = {
        "person_titles": ["Founder", "Owner", "Account Manager", "Project Manager"],
        "organization_num_employees_ranges": ["2,15"],
        "q_organization_keyword_tags": ["marketing", "web design", "branding", "seo"],
    }
    return await client.search_people(payload)
