from pydantic import BaseModel, Field

class AnalysisResponseSchema(BaseModel):
        """Defines the json response schema for the model"""
        title: str = Field(description="A short descriptive title for the analysis")
        tags: list[str] = Field(description="A list of 3-5 relevant tags for the problem solved")
        praise: str = Field(description="A short text commending the student on the things they got right")
        diagnosis: str = Field(description="A short text highlighting what the student got wrong")
        explanation: str = Field(description="An explanation of what the student got wrong using a real-world analogy")
        practice_problem: str = Field(description="A practice problem similar to the original problem")

class GymResponseSchema(BaseModel):
    """Defines the json response schema for the gym solution"""
    is_correct: bool = Field(description="Indicates if the attempt is correct")
    feedback: str = Field(description="Feedback on the provided attempt")
    solution: str = Field(description="The step-by-step solution in LaTeX format")
    next_question: str = Field(description="A follow-up question to further challenge the student. Make it harder if is_correct is true, easier if false.")
