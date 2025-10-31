"""Intent detection for routing user messages to appropriate agents."""

import re
from typing import List, Dict, Any
from enum import Enum


class IntentType(Enum):
    """Available intent types."""
    SHOPPING = "shopping"
    PAYMENT = "payment"
    UNKNOWN = "unknown"


class IntentDetector:
    """Enhanced intent detection with pattern matching and confidence scoring."""
    
    def __init__(self):
        self.keywords = {
            IntentType.PAYMENT: [
                # English keywords
                'pay', 'payment', 'card', 'checkout', 'otp', 'verify',
                'confirm purchase', 'complete order', 'transaction',
                'billing', 'invoice', 'receipt',
                
                # Chinese keywords
                '付款', '支付', '付錢', '結帳', '驗證碼', '驗證',
                '確認購買', '完成訂單', '交易', '帳單', '收據'
            ],
            
            IntentType.SHOPPING: [
                # English keywords
                'buy', 'purchase', 'shop', 'product', 'item', 'store',
                'cart', 'add to cart', 'order', 'catalog', 'browse',
                'recommendation', 'suggest',
                
                # Chinese keywords
                '買', '購買', '商品', '產品', '店', '購物', '買東西',
                '購物車', '加入購物車', '訂單', '目錄', '瀏覽',
                '推薦', '建議',
                
                # Product names
                'iphone', 'macbook', 'airpods', 'apple watch', 
                'phone', 'laptop', 'computer', 'tablet'
            ]
        }
        
        # Patterns for more complex matching
        self.patterns = {
            IntentType.PAYMENT: [
                r'(我要|想要|要).*付款',
                r'proceed.*payment',
                r'complete.*purchase',
                r'verify.*otp',
                r'\b\d{6}\b',  # OTP pattern
            ],
            
            IntentType.SHOPPING: [
                r'(我要|想要|要).*(買|購買)',
                r'(搜尋|找|查).*(商品|產品)',
                r'show.*product',
                r'search.*for',
                r'add.*cart',
            ]
        }
    
    def detect_intent(self, message: str) -> Dict[str, Any]:
        """
        Detect user intent from message with confidence scoring.
        
        Args:
            message: User's message text
            
        Returns:
            Dict with intent, confidence, and matched keywords
        """
        message_lower = message.lower().strip()
        
        if not message_lower:
            return {
                "intent": IntentType.UNKNOWN,
                "confidence": 0.0,
                "matched_keywords": [],
                "matched_patterns": []
            }
        
        intent_scores = {intent: 0.0 for intent in IntentType}
        matched_data = {intent: {"keywords": [], "patterns": []} for intent in IntentType}
        
        # Keyword matching
        for intent, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword.lower() in message_lower:
                    intent_scores[intent] += 1.0
                    matched_data[intent]["keywords"].append(keyword)
        
        # Pattern matching (higher weight)
        for intent, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    intent_scores[intent] += 2.0
                    matched_data[intent]["patterns"].append(pattern)
        
        # Find best match
        best_intent = max(intent_scores, key=intent_scores.get)
        best_score = intent_scores[best_intent]
        
        # Calculate confidence (normalize by message length and matches)
        if best_score > 0:
            max_possible_score = len(message_lower.split()) * 2
            confidence = min(best_score / max_possible_score, 1.0)
        else:
            confidence = 0.0
            best_intent = IntentType.SHOPPING  # Default to shopping
        
        # Priority adjustment: payment has highest priority if any match
        if intent_scores[IntentType.PAYMENT] > 0:
            best_intent = IntentType.PAYMENT
            confidence = max(confidence, 0.8)
        
        return {
            "intent": best_intent,
            "confidence": confidence,
            "matched_keywords": matched_data[best_intent]["keywords"],
            "matched_patterns": matched_data[best_intent]["patterns"],
            "all_scores": {intent.value: score for intent, score in intent_scores.items()}
        }
    
    def get_intent_explanation(self, detection_result: Dict[str, Any]) -> str:
        """Get human-readable explanation of intent detection."""
        intent = detection_result["intent"]
        confidence = detection_result["confidence"]
        keywords = detection_result["matched_keywords"]
        patterns = detection_result["matched_patterns"]
        
        explanation = f"Detected intent: {intent.value} (confidence: {confidence:.2f})"
        
        if keywords:
            explanation += f"\nMatched keywords: {', '.join(keywords)}"
        
        if patterns:
            explanation += f"\nMatched patterns: {len(patterns)} pattern(s)"
        
        return explanation