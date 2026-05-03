# simple test end points
# api/views.py
import base64
import io
import json
import os
import requests
from django.core.files.base import ContentFile
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import connection
from rest_framework.views import APIView

from .models import User, GeneratedImage, EditedImage, ImageScore, AuditLog, ForensicRequest, Conversation, ForensicCritique
from .serializers import (
    UserSerializer, RegisterSerializer, GeneratedImageSerializer, EditedImageSerializer,
    ImageScoreSerializer, AuditLogSerializer, ForensicRequestSerializer
)
from .ml_service import MLService
from django.conf import settings

COLAB_ML_URL = settings.COLAB_ML_URL

def pil_to_content_file(image, filename):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return ContentFile(buffer.getvalue(), name=filename)


def pil_image_to_png_data_url(image) -> str:
    """PNG data URL for SPA <img src>; avoids broken /media/ links when DEBUG=False or mixed content."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def normalize_ml_base_url(url):
    base = (url or "").strip().rstrip("/")
    for suffix in ("/generate", "/edit", "/age", "/analyze", "/critic"):
        if base.endswith(suffix):
            base = base.rsplit("/", 1)[0]
    return base


def call_remote_critic(image_b64, prompt, suspect_profile=None, route_used="generate", scores=None, metadata=None):
    ml_config = getattr(settings, 'ML_CONFIG', {})
    if not ml_config.get('ENABLE_FORENSIC_CRITIC', True) or not COLAB_ML_URL:
        return None

    base = normalize_ml_base_url(COLAB_ML_URL)
    try:
        resp = requests.post(
            f"{base}/critic",
            json={
                "image_base64": image_b64,
                "suspect_profile": suspect_profile or {},
                "prompt": prompt or "",
                "route_used": route_used,
                "scores": scores or {},
                "metadata": metadata or {},
            },
            headers={
                "ngrok-skip-browser-warning": "1",
                "User-Agent": "SmartSketch-Django/1.0",
            },
            timeout=90,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return data.get("critic_report")
            if data.get("decision"):
                return data
    except Exception as critic_e:
        print(f"Critic service failed: {critic_e}")
    return None


def save_critique(report, generated=None, edited=None):
    if not report:
        return None
    try:
        critic_score = None if report.get("score") is None else float(report.get("score"))
    except (TypeError, ValueError):
        critic_score = None
    return ForensicCritique.objects.create(
        image=generated,
        edited_image=edited,
        model_name=report.get("model", ""),
        decision=report.get("decision", "accept"),
        score=critic_score,
        issues=report.get("issues") or [],
        matched_features=report.get("matched_features") or [],
        missing_features=report.get("missing_features") or [],
        prompt_adjustment=report.get("prompt_adjustment") or "",
        safety_flags=report.get("safety_flags") or [],
        reasoning_summary=report.get("reasoning_summary") or "",
        raw_report=report,
    )

# Simple registration view
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)

class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

# Example: List generated images for user
class MyGeneratedImagesView(generics.ListAPIView):
    serializer_class = GeneratedImageSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return GeneratedImage.objects.filter(user=self.request.user).order_by('-created_at')

# Admin-only view example
class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.is_superuser:
            return AuditLog.objects.all().order_by('-timestamp')
        return AuditLog.objects.filter(user=user).order_by('-timestamp')

# Forensic request create
class ForensicRequestCreateView(generics.CreateAPIView):
    serializer_class = ForensicRequestSerializer
    permission_classes = (IsAuthenticated,)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# Approve forensic request (admin only)
class ForensicApproveView(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request, pk):
        user = request.user
        if user.role != 'admin' and not user.is_superuser:
            return Response({'detail':'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        try:
            req = ForensicRequest.objects.get(pk=pk)
        except ForensicRequest.DoesNotExist:
            return Response({'detail':'Not found'}, status=status.HTTP_404_NOT_FOUND)
        req.is_approved = True
        req.approved_at = timezone.now()
        req.save()
        return Response({'detail':'approved'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_forensic_sketch(request):
    user = request.user

    # Role check removed to allow testing on Free Tier
    # if user.role != "forensic" and not user.is_superuser:
    #     return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    prompt = request.data.get("prompt")
    case_type = request.data.get("case_type", "criminal")
    age = request.data.get("age")
    output_type = request.data.get("output_type", "photo")

    if not prompt:
        return Response({"error": "prompt is required"}, status=status.HTTP_400_BAD_REQUEST)

    if age is not None and age != "":
        try:
            age = int(age)
        except (TypeError, ValueError):
            return Response({"error": "age must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        age = 30  # Default age

    # ================================================================
    # 1. Try Colab ML Service First (Primary)
    # ================================================================
    if COLAB_ML_URL:
        # Strip any path suffix (e.g. /generate) so we always get the bare base URL,
        # then append the correct route.  Works regardless of what the user pasted in .env.
        _base = normalize_ml_base_url(COLAB_ML_URL)
        ml_url = f"{_base}/generate"
        try:
            ml_resp = requests.post(
                ml_url,
                json={"prompt": prompt, "case_type": case_type, "age": age},
                headers={
                    "ngrok-skip-browser-warning": "1",
                    "User-Agent": "SmartSketch-Django/1.0",
                },
                timeout=120,
            )
            
            if ml_resp.status_code == 200:
                ml_data = ml_resp.json()
                if ml_data.get("success"):
                    image_b64 = ml_data.get("image_base64")
                    if image_b64:
                        image_bytes = base64.b64decode(image_b64)
                        generation_id = ml_data.get("generation_id") or "forensic"
                        image_file = ContentFile(image_bytes, name=f"{generation_id}.png")

                        generated = GeneratedImage.objects.create(
                            user=user,
                            prompt=prompt,
                            image_file=image_file,
                            generation_id=generation_id,
                            seed=ml_data.get("metadata", {}).get("seed"),
                            model_version=ml_data.get("metadata", {}).get("model_version", "colab-v1"),
                            forensic_hash=ml_data.get("forensic_hash"),
                            is_watermarked=ml_data.get("is_watermarked", False),
                        )

                        scores = ml_data.get("scores") or {}
                        critic_report = ml_data.get("critic_report") or call_remote_critic(
                            image_b64=image_b64,
                            prompt=prompt,
                            route_used="generate",
                            scores=scores,
                            metadata=ml_data.get("metadata", {}),
                        )
                        save_critique(critic_report, generated=generated)

                        ImageScore.objects.create(
                            image=generated,
                            clip_score=scores.get("clip_score"),
                            identity_score=scores.get("identity_score"),
                            final_score=scores.get("combined_score"),
                        )

                        AuditLog.objects.create(
                            user=user,
                            action="generate",
                            ip_address=request.META.get("REMOTE_ADDR"),
                            prompt_used=prompt,
                            image=generated,
                        )

                        return Response(
                            {
                                "id": generated.id,
                                "image_url": f"data:image/png;base64,{image_b64}",
                                "scores": scores,
                                "metadata": ml_data.get("metadata", {}),
                                "generation_id": generation_id,
                                "forensic_hash": ml_data.get("forensic_hash"),
                                "is_watermarked": ml_data.get("is_watermarked", False),
                                "critic_report": critic_report,
                                "provider": "colab"
                            },
                            status=status.HTTP_200_OK,
                        )
            print(f"⚠️ Colab ML service returned status {ml_resp.status_code}")
        except Exception as colab_e:
            print(f"⚠️ Colab ML service failed: {colab_e}")

    # ================================================================
    # 2. Try Local ML Engine as Fallback (if enabled)
    # ================================================================
    ml_config = getattr(settings, 'ML_CONFIG', {})
    if ml_config.get('USE_LOCAL_ML', False):
        try:
            pipeline = MLService.get_pipeline()
            ml_data = pipeline.generate_sketch(
                prompt=prompt,
                case_type=case_type,
                age=age,
                output_type=output_type
            )
            
            if ml_data.get("success"):
                final_image = ml_data.get("image")
                generation_id = ml_data.get("generation_id")
                image_file = pil_to_content_file(final_image, f"{generation_id}.png")

                generated = GeneratedImage.objects.create(
                    user=user,
                    prompt=prompt,
                    image_file=image_file,
                    generation_id=generation_id,
                    seed=ml_data.get("metadata", {}).get("seed"),
                    model_version=ml_data.get("metadata", {}).get("model_version", "local-v1"),
                    forensic_hash=ml_data.get("forensic_hash"),
                    is_watermarked=ml_data.get("is_watermarked", False),
                )
                critic_report = ml_data.get("critic_report")
                save_critique(critic_report, generated=generated)

                scores = ml_data.get("scores") or {}
                ImageScore.objects.create(
                    image=generated,
                    clip_score=scores.get("clip_score"),
                    identity_score=scores.get("identity_score"),
                    final_score=scores.get("combined_score"),
                )

                AuditLog.objects.create(
                    user=user,
                    action="generate",
                    ip_address=request.META.get("REMOTE_ADDR"),
                    prompt_used=prompt,
                    image=generated,
                )

                return Response(
                    {
                        "id": generated.id,
                        "image_url": pil_image_to_png_data_url(final_image),
                        "scores": scores,
                        "metadata": ml_data.get("metadata", {}),
                        "generation_id": generation_id,
                        "forensic_hash": ml_data.get("forensic_hash"),
                        "is_watermarked": ml_data.get("is_watermarked", False),
                        "critic_report": critic_report,
                        "provider": "local"
                    },
                    status=status.HTTP_200_OK,
                )
        except Exception as local_e:
            print(f"⚠️ Local ML Engine failed: {local_e}")

    return Response(
        {"error": "ML generation failed. Colab service unavailable and local ML disabled/failed."},
        status=status.HTTP_503_SERVICE_UNAVAILABLE
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def edit_forensic_sketch(request):
    user = request.user

    # Role check removed
    # if user.role != "forensic" and not user.is_superuser:
    #     return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    original_image_id = request.data.get("original_image_id")
    edit_prompt = request.data.get("edit_prompt")
    strength = request.data.get("strength", 0.6)

    if not original_image_id or not edit_prompt:
        return Response({"error": "original_image_id and edit_prompt are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        strength = float(strength)
    except (TypeError, ValueError):
        return Response({"error": "strength must be a float"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        generated_image = GeneratedImage.objects.get(pk=original_image_id, user=user)
    except GeneratedImage.DoesNotExist:
        return Response({"error": "Original image not found"}, status=status.HTTP_404_NOT_FOUND)

    # ================================================================
    # 1. Try Colab ML Service First (Primary)
    # ================================================================
    if COLAB_ML_URL:
        _base = normalize_ml_base_url(COLAB_ML_URL)
        ml_url = f"{_base}/edit"
        try:
            with generated_image.image_file.open('rb') as f:
                original_image_b64 = base64.b64encode(f.read()).decode('utf-8')
            
            ml_resp = requests.post(
                ml_url,
                json={
                    "generation_id": f"gen_{generated_image.id}",
                    "original_image": original_image_b64,
                    "edit_prompt": edit_prompt,
                    "strength": strength,
                },
                headers={
                    "ngrok-skip-browser-warning": "1",
                    "User-Agent": "SmartSketch-Django/1.0",
                },
                timeout=120,
            )
            
            if ml_resp.status_code == 200:
                ml_data = ml_resp.json()
                if ml_data.get("success"):
                    edited_image_b64 = ml_data.get("edited_image")
                    if edited_image_b64:
                        edited_bytes = base64.b64decode(edited_image_b64)
                        edit_id = ml_data.get("edit_id") or f"edit_{generated_image.id}"
                        edited_file = ContentFile(edited_bytes, name=f"{edit_id}.png")

                        edited = EditedImage.objects.create(
                            user=user,
                            original_image=generated_image,
                            edit_prompt=edit_prompt,
                            edited_file=edited_file,
                            forensic_hash=ml_data.get("forensic_hash"),
                            is_watermarked=ml_data.get("is_watermarked", False),
                        )

                        scores = ml_data.get("scores") or {}
                        identity_score = ml_data.get("identity_score", 0)
                        critic_report = ml_data.get("critic_report") or call_remote_critic(
                            image_b64=edited_image_b64,
                            prompt=edit_prompt,
                            route_used=ml_data.get("route_used", "edit"),
                            scores=scores,
                            metadata={"edit_id": edit_id, "original_generation_id": generated_image.generation_id},
                        )
                        save_critique(critic_report, edited=edited)

                        ImageScore.objects.create(
                            edited_image=edited,
                            clip_score=scores.get("clip_score"),
                            identity_score=identity_score,
                            final_score=scores.get("combined_score"),
                        )

                        AuditLog.objects.create(
                            user=user,
                            action="edit",
                            ip_address=request.META.get("REMOTE_ADDR"),
                            prompt_used=edit_prompt,
                            image=generated_image,
                        )

                        return Response(
                            {
                                "id": edited.id,
                                "original_image_id": generated_image.id,
                                "edited_image_url": request.build_absolute_uri(edited.edited_file.url),
                                "edit_prompt": edit_prompt,
                                "identity_score": identity_score,
                                "scores": scores,
                                "forensic_hash": ml_data.get("forensic_hash"),
                                "is_watermarked": ml_data.get("is_watermarked", False),
                                "critic_report": critic_report,
                                "edit_id": edit_id,
                                "provider": "colab"
                            },
                            status=status.HTTP_200_OK,
                        )
        except Exception as colab_e:
            print(f"⚠️ Colab ML edit failed: {colab_e}")

    # ================================================================
    # 2. Try Local ML Engine as Fallback (if enabled)
    # ================================================================
    ml_config = getattr(settings, 'ML_CONFIG', {})
    if ml_config.get('USE_LOCAL_ML', False):
        try:
            from PIL import Image
            with generated_image.image_file.open('rb') as f:
                pil_image = Image.open(f).convert('RGB')

            pipeline = MLService.get_pipeline()
            ml_data = pipeline.edit_sketch(
                generation_id=str(generated_image.id),
                original_image=pil_image,
                edit_prompt=edit_prompt,
                strength=strength
            )

            if ml_data.get("success"):
                edited_pil = ml_data.get("edited_image")
                edit_id = ml_data.get("edit_id")
                edited_file = pil_to_content_file(edited_pil, f"{edit_id}.png")

                edited = EditedImage.objects.create(
                    user=user,
                    original_image=generated_image,
                    edit_prompt=edit_prompt,
                    edited_file=edited_file,
                    forensic_hash=ml_data.get("forensic_hash"),
                    is_watermarked=ml_data.get("is_watermarked", False),
                )

                scores = ml_data.get("scores") or {}
                identity_score = ml_data.get("identity_score", 0)
                critic_report = ml_data.get("critic_report")
                save_critique(critic_report, edited=edited)

                ImageScore.objects.create(
                    edited_image=edited,
                    clip_score=scores.get("clip_score"),
                    identity_score=identity_score,
                    final_score=scores.get("combined_score"),
                )

                AuditLog.objects.create(
                    user=user,
                    action="edit",
                    ip_address=request.META.get("REMOTE_ADDR"),
                    prompt_used=edit_prompt,
                    image=generated_image,
                )

                return Response(
                    {
                        "id": edited.id,
                        "original_image_id": generated_image.id,
                        "edited_image_url": request.build_absolute_uri(edited.edited_file.url),
                        "edit_prompt": edit_prompt,
                        "identity_score": identity_score,
                        "scores": scores,
                        "forensic_hash": ml_data.get("forensic_hash"),
                        "is_watermarked": ml_data.get("is_watermarked", False),
                        "critic_report": critic_report,
                        "edit_id": edit_id,
                        "provider": "local"
                    },
                    status=status.HTTP_200_OK,
                )
        except Exception as local_e:
            print(f"⚠️ Local ML edit failed: {local_e}")

    return Response(
        {"error": "ML edit failed. Colab service unavailable and local ML disabled/failed."},
        status=status.HTTP_503_SERVICE_UNAVAILABLE
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def age_forensic_sketch(request):
    user = request.user
    original_image_id = request.data.get("original_image_id")
    years = request.data.get("years", 10)

    if not original_image_id:
        return Response({"error": "original_image_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        years = int(years)
    except (TypeError, ValueError):
        return Response({"error": "years must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        generated_image = GeneratedImage.objects.get(pk=original_image_id, user=user)
    except GeneratedImage.DoesNotExist:
        return Response({"error": "Original image not found"}, status=status.HTTP_404_NOT_FOUND)

    # 1. Try Colab/Modal
    if COLAB_ML_URL:
        _base = normalize_ml_base_url(COLAB_ML_URL)
        ml_url = f"{_base}/age"
        try:
            with generated_image.image_file.open('rb') as f:
                original_image_b64 = base64.b64encode(f.read()).decode('utf-8')
            
            ml_resp = requests.post(
                ml_url,
                json={
                    "generation_id": f"gen_{generated_image.id}",
                    "original_image": original_image_b64,
                    "years": years,
                },
                headers={
                    "ngrok-skip-browser-warning": "1",
                    "User-Agent": "SmartSketch-Django/1.0",
                },
                timeout=120,
            )
            
            if ml_resp.status_code == 200:
                ml_data = ml_resp.json()
                if ml_data.get("success"):
                    edited_image_b64 = ml_data.get("edited_image")
                    if edited_image_b64:
                        edited_bytes = base64.b64decode(edited_image_b64)
                        edit_id = ml_data.get("edit_id") or f"age_{generated_image.id}"
                        edited_file = ContentFile(edited_bytes, name=f"{edit_id}.png")

                        edited = EditedImage.objects.create(
                            user=user,
                            original_image=generated_image,
                            edit_prompt=f"Age progression: {years} years",
                            edited_file=edited_file,
                            forensic_hash=ml_data.get("forensic_hash"),
                            is_watermarked=ml_data.get("is_watermarked", False),
                        )

                        scores = ml_data.get("scores") or {}
                        identity_score = ml_data.get("identity_score", 0)
                        critic_report = ml_data.get("critic_report") or call_remote_critic(
                            image_b64=edited_image_b64,
                            prompt=f"Age progression: {years} years",
                            route_used="age",
                            scores=scores,
                            metadata={"edit_id": edit_id, "years": years},
                        )
                        save_critique(critic_report, edited=edited)

                        ImageScore.objects.create(
                            edited_image=edited,
                            clip_score=scores.get("clip_score"),
                            identity_score=identity_score,
                            final_score=scores.get("combined_score"),
                        )

                        return Response({
                            "id": edited.id,
                            "original_image_id": generated_image.id,
                            "edited_image_url": request.build_absolute_uri(edited.edited_file.url),
                            "years": years,
                            "identity_score": identity_score,
                            "scores": scores,
                            "forensic_hash": ml_data.get("forensic_hash"),
                            "is_watermarked": ml_data.get("is_watermarked", False),
                            "critic_report": critic_report,
                            "edit_id": edit_id,
                            "provider": "colab"
                        }, status=status.HTTP_200_OK)
        except Exception as colab_e:
            print(f"⚠️ Colab ML age failed: {colab_e}")

    # 2. Try Local Fallback
    ml_config = getattr(settings, 'ML_CONFIG', {})
    if ml_config.get('USE_LOCAL_ML', False):
        try:
            from PIL import Image
            with generated_image.image_file.open('rb') as f:
                pil_image = Image.open(f).convert('RGB')

            pipeline = MLService.get_pipeline()
            ml_data = pipeline.age_progression(
                generation_id=str(generated_image.id),
                original_image=pil_image,
                years=years
            )

            if ml_data.get("success"):
                edited_pil = ml_data.get("edited_image")
                edit_id = ml_data.get("edit_id")
                edited_file = pil_to_content_file(edited_pil, f"{edit_id}.png")

                edited = EditedImage.objects.create(
                    user=user,
                    original_image=generated_image,
                    edit_prompt=f"Age progression: {years} years",
                    edited_file=edited_file,
                    forensic_hash=ml_data.get("forensic_hash"),
                    is_watermarked=ml_data.get("is_watermarked", False),
                )
                critic_report = ml_data.get("critic_report")
                save_critique(critic_report, edited=edited)

                return Response({
                    "id": edited.id,
                    "original_image_id": generated_image.id,
                    "edited_image_url": request.build_absolute_uri(edited.edited_file.url),
                    "years": years,
                    "forensic_hash": ml_data.get("forensic_hash"),
                    "is_watermarked": ml_data.get("is_watermarked", False),
                    "critic_report": critic_report,
                    "edit_id": edit_id,
                    "provider": "local"
                }, status=status.HTTP_200_OK)
        except Exception as local_e:
            print(f"⚠️ Local ML age failed: {local_e}")

    return Response(
        {"error": "ML age failed. Colab service unavailable and local ML disabled/failed."},
        status=status.HTTP_503_SERVICE_UNAVAILABLE
    )

def _forensic_agent_chat_payload(user, message, thread_id, case_number, request):
    """
    Run the LangGraph forensic agent, persist any image, return the same dict
    the JSON /forensic/chat/ endpoint returns (without the Response wrapper).
    """
    from PIL import Image as PilImage
    import uuid as _uuid

    if thread_id:
        conversation, _ = Conversation.objects.get_or_create(
            thread_id=thread_id,
            user=user,
            defaults={"case_number": case_number},
        )
    else:
        thread_id = "thread_" + _uuid.uuid4().hex[:8]
        conversation = Conversation.objects.create(
            thread_id=thread_id,
            user=user,
            case_number=case_number or ("CASE-" + _uuid.uuid4().hex[:4].upper()),
        )

    agent = MLService.get_agent()
    final_state = agent.run(message, thread_id=thread_id)

    profile = final_state.get("suspect_profile")
    image_data = final_state.get("current_image")
    gen_id = final_state.get("generation_id") or ("agent_" + thread_id)
    gen_params = final_state.get("generation_params") or {}
    critic_report = final_state.get("critic_report")
    modal_scores = gen_params.get("modal_scores") or {}

    last_score_out = final_state.get("last_score")
    if last_score_out is None and modal_scores.get("combined_score") is not None:
        try:
            last_score_out = float(modal_scores["combined_score"])
        except (TypeError, ValueError):
            pass
    identity_out = gen_params.get("last_identity_score")
    if identity_out is None and modal_scores.get("identity_score") is not None:
        try:
            identity_out = float(modal_scores["identity_score"])
        except (TypeError, ValueError):
            pass

    image_url = None
    saved_image_id = None

    if image_data is not None:
        try:
            if isinstance(image_data, str):
                pil_img = PilImage.open(
                    io.BytesIO(base64.b64decode(image_data))
                ).convert("RGB")
            elif isinstance(image_data, PilImage.Image):
                pil_img = image_data
            else:
                pil_img = None

            if pil_img is not None:
                image_file = pil_to_content_file(pil_img, gen_id + ".png")
                generated = GeneratedImage.objects.create(
                    user=user,
                    prompt=profile.to_detailed_prompt() if profile else message,
                    image_file=image_file,
                    model_version="agent-sdxl-v1",
                    generation_id=gen_id,
                )
                save_critique(critic_report, generated=generated)
                ImageScore.objects.create(
                    image=generated,
                    identity_score=identity_out,
                    final_score=last_score_out,
                )
                AuditLog.objects.create(
                    user=user,
                    action="generate",
                    ip_address=request.META.get("REMOTE_ADDR"),
                    prompt_used=message,
                    image=generated,
                )
                image_url = pil_image_to_png_data_url(pil_img)
                saved_image_id = generated.id
                print("[AgentChat] Image saved id=" + str(saved_image_id))
        except Exception as save_err:
            print("[AgentChat] Image save failed: " + str(save_err))

    return {
        "status": "success",
        "thread_id": thread_id,
        "case_number": conversation.case_number,
        "suspect_profile": profile.model_dump() if profile else {},
        "image_url": image_url,
        "image_id": saved_image_id,
        "generation_id": gen_id,
        "identity_score": identity_out,
        "last_score": last_score_out,
        "ml_scores": modal_scores,
        "is_verified": final_state.get("is_verified", False),
        "next_step": final_state.get("next_step"),
        "iteration": final_state.get("iteration_count"),
        "last_error": final_state.get("last_error"),
        "critic_report": critic_report,
        "verification_history": final_state.get("verification_history") or [],
    }


def _sse_chunk(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def agent_chat_stream(request):
    """
    Same body as /forensic/chat/ but streams Server-Sent Events for the Forensic Console UI.
    """
    user = request.user
    message = request.data.get("message")
    thread_id = request.data.get("thread_id")
    case_number = request.data.get("case_number")

    if not message:
        return Response(
            {"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    def event_stream():
        try:
            yield _sse_chunk(
                "status",
                {"stage": "analyze", "message": "[Analyzer] Analyzing suspect description..."},
            )
            yield _sse_chunk(
                "status",
                {"stage": "modal", "message": "[Modal] Contacting remote ML service..."},
            )
            yield _sse_chunk(
                "progress",
                {
                    "stage": "artist",
                    "message": "[Artist] Running forensic sketch agent (may take a minute)...",
                    "percent": 40,
                },
            )
            payload = _forensic_agent_chat_payload(
                user, message, thread_id, case_number, request
            )
            yield _sse_chunk(
                "status",
                {
                    "stage": "verify",
                    "message": "[Verify] Quality check complete.",
                    "percent": 92,
                },
            )
            yield _sse_chunk("result", payload)
        except Exception as e:
            print("[Agent Stream Error] " + str(e))
            import traceback

            traceback.print_exc()
            yield _sse_chunk("error", {"error": str(e)})

    resp = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agent_chat(request):
    """
    Stateful conversational endpoint for the Forensic Agent.

    Request body:
        { "message": str, "thread_id": str (optional), "case_number": str (optional) }

    Response:
        { "status", "thread_id", "case_number", "suspect_profile",
          "image_url", "image_id", "generation_id", "identity_score",
          "last_score", "is_verified", "next_step", "iteration", "last_error" }
    """
    user = request.user
    message = request.data.get("message")
    thread_id = request.data.get("thread_id")
    case_number = request.data.get("case_number")

    if not message:
        return Response({"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payload = _forensic_agent_chat_payload(
            user, message, thread_id, case_number, request
        )
        return Response(payload, status=status.HTTP_200_OK)
    except Exception as e:
        print("[Agent Error] " + str(e))
        import traceback

        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------------
# Sketch style conversion  (CPU — no GPU cost)
# ---------------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sketch_style_view(request):
    """
    POST { generation_id, style: 'pencil' | 'charcoal' }
    Returns { styled_image_url }
    """
    generation_id = request.data.get('generation_id')
    style = request.data.get('style', 'pencil')

    if not generation_id:
        return Response({'error': 'generation_id required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        generated = GeneratedImage.objects.get(generation_id=generation_id, user=request.user)
    except GeneratedImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        from PIL import Image as PilImage
        import cv2, numpy as np

        img = PilImage.open(generated.image_file).convert('RGB')

        # Fast CPU sketch — no GPU needed for style toggle
        img_arr = np.array(img)
        gray = cv2.cvtColor(img_arr, cv2.COLOR_RGB2GRAY)
        inverted = 255 - gray
        blur_size = {'pencil': (21, 21), 'charcoal': (31, 31)}.get(style, (21, 21))
        blurred = cv2.GaussianBlur(inverted, blur_size, 0)
        sketch_arr = cv2.divide(gray, 255 - blurred, scale=256.0)

        if style == 'charcoal':
            # darken + add texture for charcoal look
            sketch_arr = np.clip(sketch_arr.astype(float) * 0.75, 0, 255).astype(np.uint8)

        sketch_img = PilImage.fromarray(sketch_arr).convert('RGB')

        filename = f"{generation_id}_{style}.png"
        content_file = pil_to_content_file(sketch_img, filename)

        # Save as a new GeneratedImage variant
        styled = GeneratedImage.objects.create(
            user=request.user,
            prompt=generated.prompt + f' [{style}]',
            image_file=content_file,
            model_version=f'sketch-{style}',
            generation_id=f'{generation_id}_{style}',
        )
        styled_url = request.build_absolute_uri(styled.image_file.url)
        return Response({'styled_image_url': styled_url, 'style': style})

    except Exception as e:
        import traceback; traceback.print_exc()
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------------
# PDF Forensic Report Export
# ---------------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def export_report_view(request):
    """
    POST { generation_id }
    Returns a PDF binary (application/pdf)
    """
    generation_id = request.data.get('generation_id')
    if not generation_id:
        return Response({'error': 'generation_id required'}, status=status.HTTP_400_BAD_REQUEST)

    # Try to find the image (generation or edit id)
    generated = None
    try:
        generated = GeneratedImage.objects.get(generation_id=generation_id, user=request.user)
    except GeneratedImage.DoesNotExist:
        # Maybe it's an edit id stored as generation_id on a variant
        try:
            generated = GeneratedImage.objects.filter(
                user=request.user
            ).order_by('-created_at').first()
        except Exception:
            pass

    if not generated:
        return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from PIL import Image as PilImage
        import datetime

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm,
                                leftMargin=2*cm, rightMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # Header
        title_style = ParagraphStyle('title', parent=styles['Title'], fontSize=20,
                                     textColor=colors.HexColor('#111827'), alignment=TA_CENTER)
        sub_style = ParagraphStyle('sub', parent=styles['Normal'], fontSize=10,
                                   textColor=colors.HexColor('#6B7280'), alignment=TA_CENTER)

        story.append(Paragraph('SMARTSKETCH AI', title_style))
        story.append(Paragraph('Forensic Sketch Report — RESEARCH USE ONLY', sub_style))
        story.append(Spacer(1, 0.5*cm))

        # Case metadata table
        score_obj = ImageScore.objects.filter(image=generated).first()
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')
        data = [
            ['Generated:', now],
            ['Generation ID:', str(generated.generation_id or generation_id)],
            ['Model:', str(generated.model_version or 'SDXL-1.0')],
            ['Operator:', str(request.user.username)],
            ['Prompt:', str(generated.prompt or '—')],
        ]
        if score_obj:
            if score_obj.final_score:
                data.append(['Quality Score:', f'{score_obj.final_score:.1f}/100'])
            if score_obj.identity_score:
                data.append(['Identity Score:', f'{float(score_obj.identity_score)*100:.1f}%'])
        critique = generated.critiques.order_by('-created_at').first()
        if critique:
            data.append(['Critic Decision:', str(critique.decision).title()])
            if critique.score is not None:
                data.append(['Critic Score:', f'{float(critique.score):.1f}/100'])
            if critique.reasoning_summary:
                data.append(['Critic Notes:', str(critique.reasoning_summary)])

        tbl = Table(data, colWidths=[4*cm, 13*cm])
        tbl.setStyle(TableStyle([
            ('FONTNAME',  (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE',  (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6B7280')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#111827')),
            ('FONTNAME',  (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#F9FAFB'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#E5E7EB')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.5*cm))

        # Image
        img_file = generated.image_file
        pil_img = PilImage.open(img_file)
        img_buf = io.BytesIO()
        pil_img.save(img_buf, format='PNG')
        img_buf.seek(0)
        rl_img = RLImage(img_buf, width=10*cm, height=10*cm)
        rl_img.hAlign = 'CENTER'
        story.append(rl_img)
        story.append(Spacer(1, 0.4*cm))

        # Footer / integrity
        footer_style = ParagraphStyle('footer', parent=styles['Normal'], fontSize=7,
                                      textColor=colors.HexColor('#9CA3AF'), alignment=TA_CENTER)
        story.append(Paragraph(
            'This document was generated by SmartSketch AI and is intended for law enforcement research purposes only. '
            'The AI-generated sketch may not accurately represent the described individual.',
            footer_style
        ))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            f'SmartSketch AI • {now} • Forensic Hash: {generation_id}',
            footer_style
        ))

        doc.build(story)
        buf.seek(0)

        from django.http import HttpResponse
        response = HttpResponse(buf.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="SmartSketch_{generation_id}.pdf"'
        return response

    except ImportError:
        return Response(
            {'error': 'reportlab not installed. Run: pip install reportlab'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ---------------------------------------------------------------------------
# Health Check (Smoke Test)
# ---------------------------------------------------------------------------
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """
    Returns 200 OK if the API and Database are healthy.
    """
    health = {
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "database": "connected"
    }
    try:
        connection.ensure_connection()
    except Exception as e:
        health["status"] = "unhealthy"
        health["database"] = f"error: {str(e)}"
        return Response(health, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(health, status=status.HTTP_200_OK)
