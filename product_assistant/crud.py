class DatabaseModel():
    def get_document(queryset,filter={},field_list=[]):
        data = queryset(**filter).limit(1).only(*field_list)
        if len(data):
            data = data[0]
        else:
            data = None
        return data
    
    def list_documents(queryset,filter={},field_list=[],sort_list = [],lower_limit = None, upper_limit = None):
        data = queryset(**filter).skip(lower_limit).limit(upper_limit - lower_limit if lower_limit != None and upper_limit != None else None).only(*field_list).order_by(*sort_list)
        return data
    
    def update_documents(queryset, filter={}, json={}):
        data = queryset(**filter).update(**json)
        return bool(data)
    
    def save_documents(queryset,  json={}):
        obj = queryset(**json)
        obj.save()
        return obj

    def delete_documents(queryset,  json={}):
        queryset(**json).delete()
        return True
    def count_documents(queryset,filter={}):
        count = queryset(**filter).count()
        return count