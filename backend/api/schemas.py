from pydantic import BaseModel, Field

class AnalysisResponseSchema(BaseModel):
	"""Defines the json response schema for the model"""
	title: str = Field(description="A short descriptive title for the analysis")
	tags: list[str] = Field(description="A list of 3-5 relevant tags for the problem solved")
	praise: str = Field(description="A short text commending the student on the things they got right")
	diagnosis: str = Field(description="A short text highlighting what the student got wrong")
	explanation: str = Field(description="An explanation of what the student got wrong using a real-world analogy")
	#practice_problem: str = Field(description="A practice problem similar to the original problem")

class GymResponseSchema(BaseModel):
    """Defines the json response schema for the gym solution"""
    is_correct: bool = Field(description="Indicates if the attempt is correct. Respond 'True' or 'False'")
    feedback: str = Field(description="Feedback on the provided attempt")
    solution: str = Field(description="The step-by-step solution in LaTeX format")
    next_question: str = Field(description="A follow-up question to further challenge the student. Make it harder if is_correct is true, easier if false.")
     

class GymGenerateMCQResponseSchema(BaseModel):
    """Defines the json response schema for the gym question generation"""
    question_text: str = Field(description="The main text/question been asked")
    options: list[str] = Field(description="A list of exactly 4 options one of which must be the correct answer to the question_text. Make sure the other options are similar but incorrect.")
    correct_answer: str = Field(description="The correct answer to the question_text. This should match one of the correct answer exactly .")
    
class GymGenerateOpenEndedResponseSchema(BaseModel):
	"""Defines the json response schema for the gym question generation"""
	question_text: str = Field(description="The main text/question been asked")
	answer_guide: str = Field(description="A step-by-step guide to how the question can be solved. This should be in LaTeX format if there are any math expressions.")
     
class GymGenerateMCQListSchema(BaseModel):
    questions: list[GymGenerateMCQResponseSchema]

class GymGenerateOpenEndedListSchema(BaseModel):
    questions: list[GymGenerateOpenEndedResponseSchema]

class GymEvaluateOpenEndedResponseSchema(BaseModel):
    """Defines the json response schema for grading open ended questions"""
    is_correct: bool = Field(description="Whether the user's response is correct or generally meets the rubric")
    score: float = Field(description="The score assigned to the user out of 100 based on the rubric")
    feedback: str = Field(description="Actionable, encouraging feedback on the user's attempt explaining what they got right and wrong")
