import db
import db.dataset
import db.exceptions
import sqlalchemy

KEY_LENGTH = 40


def submit(hl_model_id, user_id, is_correct, suggestion=None):
    if hl_model_id is None or is_correct is None or user_id is None:
        raise ValueError("Missing required data")
    if type(hl_model_id) is not int:
        raise ValueError("`hl_model_id` argument must be an integer")
    if type(user_id) is not int:
        raise ValueError("`user_id` argument must be an integer")
    if type(is_correct) is not bool:
        raise ValueError("`is_correct` argument must be a boolean")
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO feedback (highlevel_model_id, user_id, correct, suggestion)
                 VALUES (:highlevel_model_id, :user_id, :correct, :suggestion)
         ON CONFLICT ON CONSTRAINT feedback_pkey
              DO UPDATE SET (correct, suggestion) = (:correct, :suggestion)
                  WHERE feedback.highlevel_model_id = :highlevel_model_id AND feedback.user_id = :user_id
        """), {
            "highlevel_model_id": hl_model_id,
            "user_id": user_id,
            "correct": is_correct,
            "suggestion": suggestion,
        })
