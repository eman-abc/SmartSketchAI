# ============================================
# CELL: Create Corrected pipeline.py
# ============================================

import random
from datetime import datetime
from typing import Dict, Optional, Literal
from PIL import Image

from .validator import ForensicPromptValidator
from .generator import FaceGenerator
from .scorer import FaceScorer
from .sketch_converter import MemoryEfficientSketchConverter
from .inpainter import FaceInpainter
from .integrity import ForensicSigner, ForensicSafetyChecker
from .restorer import FaceRestorer


class SmartSketchPipeline:
    """
    Complete SmartSketch pipeline with sketch generation and face editing
    """
    
    def __init__(
        self,
        validator: ForensicPromptValidator,
        generator: FaceGenerator,
        scorer: FaceScorer,
        sketch_converter: Optional[MemoryEfficientSketchConverter] = None,
        face_editor: Optional["FaceEditor"] = None,
        face_inpainter: Optional[FaceInpainter] = None,
        forensic_signer: Optional[ForensicSigner] = None,
        safety_checker: Optional[ForensicSafetyChecker] = None,
        face_restorer: Optional[FaceRestorer] = None
    ):
        """
        Initialize pipeline
        
        Args:
            validator: ForensicPromptValidator instance
            generator: FaceGenerator instance
            scorer: FaceScorer instance
            sketch_converter: SketchConverter instance (optional)
            face_editor: FaceEditor instance (optional)
        """
        self.validator = validator
        self.generator = generator
        self.scorer = scorer
        self.sketch_converter = sketch_converter
        self.face_editor = face_editor
        self.face_inpainter = face_inpainter
        self.signer = forensic_signer or ForensicSigner()
        self.safety_checker = safety_checker
        self.face_restorer = face_restorer
        
        print("=" * 60)
        print("READY SmartSketch Pipeline Initialized")
        print("=" * 60)
        print("[OK] CLIP Scorer Ready")
        print("[OK] Face Embedding Model Ready")
        print("READY Scorer Initialized")
        
        if face_editor:
            print("[OK] Face Editor: Ready")
        else:
            print("[WARNING] Face Editor: Not loaded")
        
        if sketch_converter:
            print("[OK] Sketch Converter: Ready")
        else:
            print("[WARNING] Sketch Converter: Not loaded (photos only)")
        
        print("=" * 60)
    
    def generate_sketch(
        self,
        prompt: str,
        case_type: str = "criminal",
        age: Optional[int] = None,
        seed: Optional[int] = None,
        num_inference_steps: int = 30,
        output_type: Literal["photo", "sketch"] = "photo",
        sketch_style: Literal["pencil", "charcoal", "forensic"] = "forensic",
        sketch_method: Literal["simple", "controlnet"] = "controlnet"
    ) -> Dict:
        """
        Main pipeline with sketch support
        
        Args:
            prompt: User's text description
            case_type: "criminal" or "missing"
            age: Person's age
            seed: Random seed
            num_inference_steps: Generation quality
            output_type: "photo" or "sketch"
            sketch_style: Style if output_type="sketch"
            sketch_method: "simple" (fast) or "controlnet" (quality)
        
        Returns:
            Result dictionary
        """
        
        # Generate unique ID
        generation_id = f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        timestamp = datetime.now().isoformat()
        
        # ============================================
        # STEP 1: VALIDATE & ENHANCE
        # ============================================
        
        is_valid, enhanced_prompt, validation_meta = self.validator.validate_and_enhance(
            prompt=prompt,
            case_type=case_type,
            age=age
        )
        
        if not is_valid:
            return {
                "success": False,
                "generation_id": generation_id,
                "error": validation_meta['reason'],
                "timestamp": timestamp
            }
        
        # ============================================
        # STEP 2: GENERATE PHOTOREALISTIC FACE
        # ============================================
        
        try:
            if seed is None:
                seed = random.randint(0, 999999)
            
            photo_image = self.generator.generate_face(
                prompt=enhanced_prompt,
                seed=seed,
                num_inference_steps=num_inference_steps
            )

            # --- Step 2b: Face Restoration ---
            if self.face_restorer:
                print("[INFO] Enhancing facial features with GFPGAN...")
                photo_image = self.face_restorer.restore(photo_image)

            
        except Exception as e:
            return {
                "success": False,
                "generation_id": generation_id,
                "error": f"Generation failed: {str(e)}",
                "timestamp": timestamp
            }
        
        # ============================================
        # STEP 3: CONVERT TO SKETCH (if requested)
        # ============================================
        
        final_image = photo_image
        conversion_metadata = {}
        
        if output_type == "sketch":
            if self.sketch_converter is None:
                return {
                    "success": False,
                    "generation_id": generation_id,
                    "error": "Sketch converter not initialized",
                    "timestamp": timestamp
                }
            
            try:
                print(f"\n[INFO] Converting to {sketch_style} sketch...")
                
                sketch_image = self.sketch_converter.convert(
                    image=photo_image,
                    method=sketch_method,
                    style=sketch_style,
                    seed=seed
                )
                
                final_image = sketch_image
                conversion_metadata = {
                    "sketch_style": sketch_style,
                    "sketch_method": sketch_method,
                    "converted_from_photo": True
                }
                
                print("[OK] Sketch conversion complete!")
                
            except Exception as e:
                return {
                    "success": False,
                    "generation_id": generation_id,
                    "error": f"Sketch conversion failed: {str(e)}",
                    "timestamp": timestamp,
                    "photo_image": photo_image
                }
        
        # ============================================
        # STEP 4: FORENSIC INTEGRITY (SIGN & HASH)
        # ============================================
        print("\n[SECURITY] Applying forensic integrity...")
        
        # Safety Check (Optional)
        has_nsfw = False
        if self.safety_checker:
            final_image, has_nsfw = self.safety_checker.check(final_image)
            if has_nsfw:
                print("[WARNING] NSFW content detected. Image censored.")

        # Invisible Watermark
        final_image = self.signer.sign_image(final_image)
        
        # Calculate Hash
        forensic_hash = self.signer.calculate_hash(final_image)

        # ============================================
        # STEP 5: SCORE THE OUTPUT
        # ============================================
        
        try:
            scores = self.scorer.score_generation(
                image=photo_image,
                prompt=enhanced_prompt
            )
        except Exception as e:
            scores = {
                "clip_score": 0.5,
                "combined_score": 50.0,
                "interpretation": f"Scoring failed: {str(e)}"
            }
        
        # ============================================
        # STEP 5: COMPILE RESULTS
        # ============================================
        
        result = {
            "success": True,
            "generation_id": generation_id,
            "image": final_image,
            "photo_image": photo_image,
            "output_type": output_type,
            "scores": scores,
            "forensic_hash": forensic_hash,
            "is_watermarked": True,
            "metadata": {
                "timestamp": timestamp,
                "case_type": case_type,
                "age": age,
                "seed": seed,
                "original_prompt": prompt,
                "enhanced_prompt": enhanced_prompt,
                "validation": validation_meta,
                "num_inference_steps": num_inference_steps,
                "model_version": "sdxl-lora-v1.0",
                **conversion_metadata
            }
        }
        
        return result
    
    def edit_sketch(
        self,
        generation_id: str,
        original_image: Image.Image,
        edit_prompt: str,
        strength: Optional[float] = None,
        seed: Optional[int] = None
    ) -> Dict:
        """
        Edit an existing face
        
        Args:
            generation_id: ID of original generation
            original_image: Original face image (PIL Image)
            edit_prompt: What to change (e.g., "add round glasses")
            strength: How much to change (0.0-1.0, auto if None)
            seed: Random seed for reproducibility
        
        Returns:
            Dictionary with:
            - success: bool
            - edit_id: str
            - original_image: PIL Image
            - edited_image: PIL Image
            - identity_score: float
            - scores: dict (CLIP scores)
            - metadata: dict
        """
        
        if self.face_editor is None:
            return {
                'success': False,
                'error': 'Face editor not initialized',
                'generation_id': generation_id
            }
        
        print(f"\n{'='*70}")
        print(f"[INFO] SMARTSKETCH EDIT PIPELINE")
        print(f"{'='*70}")
        print(f"📋 Original Generation ID: {generation_id}")
        print(f"📝 Edit Prompt: {edit_prompt}")
        print(f"{'='*70}")
        
        # Step 1: Validate edit prompt
        print("\nSTEP 1: VALIDATING EDIT PROMPT")
        print("-"*70)
        
        is_valid, enhanced_edit, validation_meta = self.validator.validate_and_enhance(
            prompt=edit_prompt,
            case_type="criminal",
            age=25
        )
        
        if not is_valid:
            print(f"[!] Validation failed: {validation_meta['reason']}")
            return {
                'success': False,
                'error': f"Invalid edit prompt: {validation_meta['reason']}",
                'generation_id': generation_id
            }
        
        print(f"[OK] Edit prompt validated")
        print(f"✨ Enhanced: {enhanced_edit[:80]}...")
        
        # Step 2: Edit face
        print("\nSTEP 2: EDITING FACE")
        print("-"*70)
        
        result = self.face_editor.edit_face(
            original_image=original_image,
            edit_prompt=enhanced_edit,
            strength=strength,
            seed=seed
        )

        # --- Step 2b: Face Restoration ---
        if result['success'] and self.face_restorer:
            print("[INFO] Enhancing facial features with GFPGAN...")
            result['edited_image'] = self.face_restorer.restore(result['edited_image'])

        
        if not result['success']:
            print(f"[!] Edit failed: {result['error']}")
            return result
        
        # Step 3: Score edited image
        print("\nSTEP 3: SCORING EDITED IMAGE")
        print("-"*70)
        
        try:
            scores = self.scorer.score_generation(
                image=result['edited_image'],
                prompt=enhanced_edit,
                identity_score=result.get('identity_score')
            )
            
            result['scores'] = scores
            print(f"[METRIC] Quality Score: {scores['combined_score']:.1f}/100")
            print(f"[INFO] {scores['interpretation']}")
            
        except Exception as e:
            print(f"[WARNING] Scoring failed: {e}")
            result['scores'] = {
                'clip_score': 0.0,
                'combined_score': 0.0,
                'interpretation': f"Scoring failed: {str(e)}"
            }
            
        # Step 4: Forensic Integrity
        print("\n[SECURITY] Applying forensic integrity to edit...")
        result['edited_image'] = self.signer.sign_image(result['edited_image'])
        result['forensic_hash'] = self.signer.calculate_hash(result['edited_image'])
        result['is_watermarked'] = True
        
        # Add original generation reference
        result['original_generation_id'] = generation_id
        result['metadata']['original_generation_id'] = generation_id
        result['metadata']['validation'] = validation_meta
        
        print("\n" + "="*70)
        print("[OK] EDIT PIPELINE COMPLETED SUCCESSFULLY")
        print("="*70)
        print(f"🆔 Edit ID: {result['edit_id']}")
        print(f"👤 Identity Score: {result['identity_score']:.1%}")
        print(f"📊 Quality Score: {result['scores']['combined_score']:.1f}/100")
        print(f"{'='*70}\n")
        
        return result
    
    def inpainting_edit(
        self,
        generation_id: str,
        original_image: Image.Image,
        edit_prompt: str,
        target_region: Optional[str] = None,
        strength: float = 0.75,
        seed: Optional[int] = None,
        age: int = 25,
        case_type: str = "criminal",
    ) -> Dict:
        """
        High-precision edit using semantic inpainting
        """
        if self.face_inpainter is None:
            return {'success': False, 'error': 'Inpainter not initialized'}

        # Step 1: Validate — must pass age + case_type so the validator doesn't block
        is_valid, enhanced_edit, validation_meta = self.validator.validate_and_enhance(
            prompt=edit_prompt,
            case_type=case_type,
            age=age,
        )
        if not is_valid:
            return {'success': False, 'error': f'Invalid prompt: {validation_meta.get("reason", "")}' }

        # Step 2: Inpaint
        result = self.face_inpainter.inpaint_edit(
            image=original_image,
            prompt=enhanced_edit,
            target_region=target_region,
            strength=strength,
            seed=seed
        )

        # --- Step 2b: Face Restoration ---
        if result['success'] and self.face_restorer:
            print("[INFO] Enhancing facial features with GFPGAN...")
            result['edited_image'] = self.face_restorer.restore(result['edited_image'])


        if result['success']:
            # Step 3: Score
            scores = self.scorer.score_generation(result['edited_image'], enhanced_edit)
            result['scores'] = scores
            result['generation_id'] = generation_id

            # Step 4: Forensic Integrity
            print("\n[SECURITY] Applying forensic integrity to inpaint...")
            result['edited_image'] = self.signer.sign_image(result['edited_image'])
            result['forensic_hash'] = self.signer.calculate_hash(result['edited_image'])
            result['is_watermarked'] = True

        return result

    def age_progression(
        self,
        generation_id: str,
        original_image: Image.Image,
        years: int,
        enhanced_prompt: Optional[str] = None,
        seed: Optional[int] = None
    ) -> Dict:
        """
        Perform age progression or regression
        """
        if self.face_editor is None:
            return {'success': False, 'error': 'Face editor not initialized'}

        print(f"\n[INFO] PERFORMING AGE { 'PROGRESSION' if years > 0 else 'REGRESSION' }")
        print(f"📋 Original Generation ID: {generation_id}")
        print(f"⏳ Change: {years} years")

        result = self.face_editor.age_edit(
            original_image=original_image,
            years=years,
            enhanced_prompt=enhanced_prompt,
            seed=seed
        )

        # --- Face Restoration ---
        if result['success'] and self.face_restorer:
            print("[INFO] Enhancing facial features with GFPGAN...")
            result['edited_image'] = self.face_restorer.restore(result['edited_image'])

        if result['success']:
            # Score
            scores = self.scorer.score_generation(
                image=result['edited_image'],
                prompt=result['edit_prompt'],
                identity_score=result.get('identity_score')
            )
            result['scores'] = scores
            result['generation_id'] = generation_id

            # Forensic Integrity
            print("\n[SECURITY] Applying forensic integrity to aging result...")
            result['edited_image'] = self.signer.sign_image(result['edited_image'])
            result['forensic_hash'] = self.signer.calculate_hash(result['edited_image'])
            result['is_watermarked'] = True

        return result

    @classmethod
    def from_pretrained(
        cls,
        lora_path: Optional[str] = None,
        validator_model: str = "Qwen/Qwen2.5-3B-Instruct",
        sdxl_model: str = "stabilityai/stable-diffusion-xl-base-1.0",
        lora_strength: float = 0.3,
        device: str = "cuda",
        enable_sketch: bool = True,
        enable_editing: bool = True,
        enable_inpainting: bool = True,
        enable_safety: bool = True,
        enable_restoration: bool = True,
        enable_offload: bool = False
    ):
        """
        Initialize complete pipeline
        
        Args:
            lora_path: Path to LoRA weights
            validator_model: Validator model ID
            sdxl_model: SDXL model path
            lora_strength: LoRA strength
            device: 'cuda' or 'cpu'
            enable_sketch: Load sketch converter
            enable_editing: Load face editor
        
        Returns:
            SmartSketchPipeline instance
        """
        validator = ForensicPromptValidator(validator_model, device=device)
        generator = FaceGenerator(sdxl_model, lora_path, lora_strength, device=device, enable_offload=enable_offload)
        scorer = FaceScorer(device=device)
        
        # Load sketch converter
        sketch_converter = None
        if enable_sketch:
            try:
                sketch_converter = MemoryEfficientSketchConverter(
                    base_pipeline=generator.pipe,
                    device=device,
                    enable_offload=enable_offload
                )
            except Exception as e:
                print(f"[!] Could not load sketch converter: {e}")
                print("   [INFO] Pipeline will work for photos only")
        
        # Load face editor
        face_editor = None
        if enable_editing:
            try:
                from .editor import FaceEditor
                face_editor = FaceEditor(
                    base_pipeline=generator.pipe,
                    device=device,
                    enable_offload=enable_offload
                )
            except Exception as e:
                print(f"[!] Could not load face editor: {e}")
                print("   [INFO] Editing will not be available")
        
        # Load face inpainter
        face_inpainter = None
        if enable_inpainting:
            try:
                face_inpainter = FaceInpainter(
                    base_pipeline=generator.pipe,
                    device=device,
                    enable_offload=enable_offload
                )
            except Exception as e:
                print(f"[!] Could not load face inpainter: {e}")
        
        # Load safety checker
        safety_checker = None
        if enable_safety:
            try:
                safety_checker = ForensicSafetyChecker(device=device)
            except Exception as e:
                print(f"[!] Could not load safety checker: {e}")
        
        # Load face restorer
        face_restorer = None
        if enable_restoration:
            try:
                face_restorer = FaceRestorer(
                    model_path='/models/GFPGANv1.4.pth',
                    device=device
                )
            except Exception as e:
                print(f"[!] Could not load face restorer: {e}")

        signer = ForensicSigner()
        
        return cls(validator, generator, scorer, sketch_converter, face_editor, face_inpainter, signer, safety_checker, face_restorer)


# Convenience function
def generate_forensic_sketch(
    prompt: str,
    case_type: str = "criminal",
    age: Optional[int] = None,
    seed: Optional[int] = None,
    pipeline: Optional[SmartSketchPipeline] = None,
    **kwargs
) -> Dict:
    """
    Quick generation function
    
    Args:
        prompt: Text description
        case_type: "criminal" or "missing"
        age: Person's age
        seed: Random seed for reproducibility
        pipeline: Optional pre-initialized pipeline (for performance)
        **kwargs: Additional generation parameters
    
    Returns:
        Result dictionary
    """
    if pipeline is None:
        pipeline = SmartSketchPipeline.from_pretrained()
    
    return pipeline.generate_sketch(
        prompt=prompt,
        case_type=case_type,
        age=age,
        seed=seed,
        **kwargs
    )
