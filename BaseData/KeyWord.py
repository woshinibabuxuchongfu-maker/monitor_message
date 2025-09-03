class KeyWord:
    def __init__(self, keyword: str, type: str = 'keyword'):
        self.id = None
        self.keyword = keyword
        self.type = type
        self.created_at = datetime.now()

    def __repr__(self):
        return f"KeyWord(id={self.id}, keyword='{self.keyword}', type='{self.type}', created_at={self.created_at})"