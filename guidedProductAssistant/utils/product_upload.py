import pd 
def parse_category_hierarchy(category_path):
    if not category_path or pd.isna(category_path):
        return []
    return [cat.strip() for cat in category_path.split('/')]

    