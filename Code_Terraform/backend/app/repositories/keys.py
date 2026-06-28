"""Single-table DynamoDB schema for Conduit.

Key conventions:

USER          PK=USER#<userId>           SK=PROFILE
                GSI1PK=EMAIL#<email>     GSI1SK=EMAIL
                GSI2PK=USERNAME#<name>   GSI2SK=USERNAME

FOLLOW        PK=USER#<followerId>       SK=FOLLOWS#<followedId>
                GSI2PK=USER#<followedId> GSI2SK=FOLLOWER#<followerId>

ARTICLE       PK=ARTICLE#<articleId>     SK=ARTICLE
                GSI1PK=SLUG#<slug>       GSI1SK=SLUG
                GSI2PK=AUTHOR#<authorId> GSI2SK=A#<createdAt>#<articleId>
                GSI3PK=ARTICLE_FEED      GSI3SK=<createdAt>   (global recent feed)

TAG_INDEX     PK=TAG#<tag>               SK=ARTICLE#<articleId>
                GSI1PK=TAG               GSI1SK=<tag>

FAVORITE      PK=USER#<userId>           SK=FAV#<articleId>
                GSI2PK=ARTICLE#<articleId>  GSI2SK=FAV#<userId>

COMMENT       PK=ARTICLE#<articleId>     SK=COMMENT#<commentId>
                GSI2PK=COMMENT#<commentId>  GSI2SK=COMMENT
"""

USER_PK = "USER#{user_id}"
USER_SK = "PROFILE"
EMAIL_GSI1PK = "EMAIL#{email}"
USERNAME_GSI2PK = "USERNAME#{username}"

FOLLOW_SK = "FOLLOWS#{followed_id}"
FOLLOWER_GSI2PK = "USER#{followed_id}"
FOLLOWER_GSI2SK = "FOLLOWER#{follower_id}"

ARTICLE_PK = "ARTICLE#{article_id}"
ARTICLE_SK = "ARTICLE"
SLUG_GSI1PK = "SLUG#{slug}"
AUTHOR_GSI2PK = "AUTHOR#{author_id}"
AUTHOR_GSI2SK = "A#{created_at}#{article_id}"
# Constant partition for the global "recent articles" feed; query GSI3 instead of Scan.
FEED_GSI3PK = "ARTICLE_FEED"

TAG_PK = "TAG#{tag}"
TAG_ARTICLE_SK = "ARTICLE#{article_id}"
TAG_LIST_GSI1PK = "TAG"

FAV_SK = "FAV#{article_id}"
FAV_ARTICLE_GSI2PK = "ARTICLE#{article_id}"
FAV_USER_GSI2SK = "FAV#{user_id}"

COMMENT_SK = "COMMENT#{comment_id}"
COMMENT_GSI2PK = "COMMENT#{comment_id}"
COMMENT_GSI2SK = "COMMENT"
