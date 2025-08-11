from django.http import JsonResponse
def index(request):
return JsonResponse({"status": "dataset_viewer_ok"})
