from flask import Blueprint, request, jsonify
from eliza_core import ElizaCore
from world.controller_3d import ThreeDController

eliza_scene_bp = Blueprint('eliza_scene', __name__)

@eliza_scene_bp.route('/scene', methods=['POST'])
def handle_scene():
    """
    Handles requests to create or modify 3D scenes based on Eliza's analysis.
    """
    data = request.get_json()
    if not data or 'input' not in data:
        return jsonify({"status": "error", "message": "Missing 'input' field"}), 400

    user_input = data['input']
    eliza = ElizaCore()
    controller = ThreeDController()

    # 1. Analyze input
    analysis = eliza.analyze_input(user_input)
    
    # 2. Get Eliza response (includes next_action)
    eliza_output = eliza.respond(analysis)
    
    # 3. Generate scene request
    scene_req = eliza.generate_scene_request(eliza_output)
    
    # 4. Process scene request via ThreeDController
    if scene_req:
        if 'scene' in scene_req and scene_req['scene'] == 'basic_room':
            controller.build_basic_room()
        elif 'object' in scene_req:
            controller.add_prop(scene_req['object'])
            
    # Return the full scene data
    scene_data = controller.get_scene_data()
    
    return jsonify({
        "status": "ok",
        "eliza_response": eliza_output.get("reasoning", eliza_output.get("intent", "ok")),
        "scene": scene_data
    })
