import html

# Function to strip HTML tags

def strip_html_tags(text):
    return html.escape(text)

# Use the function when parsing the episode description 
def parse_episode(episode):
    description = episode['description']  # Assuming this is where the description is stored
    clean_description = strip_html_tags(description)
    episode['description'] = clean_description
    return episode
