from rest_framework.response import Response


def serialize_data(view_set, queryset):
    serializer = view_set.serializer_class(queryset, many=True, read_only=True)
    return Response(serializer.data)


def serialize_single_obj_data(view_set, queryset):
    serializer = view_set.serializer_class(queryset, many=False, read_only=True)
    return Response(serializer.data)
