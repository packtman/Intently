# Product Requirements Document: Product Search & Catalog Protocol

**Version:** 1.0  
**Status:** Draft  
**Author:** Dipen Shah  
**Date:** January 5, 2026  
**Target Audience:** ACP Maintainers (OpenAI & Stripe)

---

## 1. Executive Summary

The **Product Search & Catalog Protocol (PSCP)** standardizes how AI agents search, browse, and compare products across ACP-compatible merchants. While merchants can be discovered via the Merchant Discovery Protocol, agents currently lack a standardized way to search products, understand product attributes, and compare offerings across different merchants.

PSCP introduces a unified product search API, standardized product data schema, and comparison capabilities that enable agents to intelligently find and evaluate products on behalf of users.

---

## 2. Problem Statement

### Current State
- Each merchant exposes products via proprietary APIs with different schemas
- Agents must implement custom integrations for each merchant's product catalog
- No standardized way to search products across multiple merchants
- Product attributes vary wildly (price format, dimensions, availability)
- Agents can't easily compare products from different merchants
- No unified taxonomy for product categories and attributes
- Product search results lack consistency in structure and metadata

### User Impact
- **Users:** Agents struggle to find the right products, miss better deals, can't compare effectively
- **Merchants:** Must build custom product APIs, harder to be discovered by agents
- **Agent Developers:** High integration complexity, maintenance burden, inconsistent data models
- **Ecosystem:** Fragmented product discovery limits ACP adoption

---

## 3. Goals & Non-Goals

### Goals
1. Standardize product search API across all ACP merchants
2. Define unified product data schema (attributes, pricing, availability)
3. Enable cross-merchant product comparison
4. Support natural language product queries
5. Provide rich product metadata (reviews, ratings, specifications)
6. Enable faceted search and filtering
7. Support product recommendations and alternatives

### Non-Goals
- Real-time inventory synchronization (merchants manage their own inventory)
- Product image hosting (merchants host images, provide URLs)
- Complex ML-based recommendation engines (agents implement their own logic)
- Product content moderation (merchants responsible for content)
- Multi-merchant cart checkout (handled separately, if at all)

---

## 4. User Stories

### As an AI Agent Developer
- I want to search products across merchants using a single API format
- I want consistent product data structures so I can build reusable comparison logic
- I want to filter products by price, availability, ratings, and attributes
- I want to understand product relationships (variants, bundles, alternatives)
- I want to handle product availability and pricing changes gracefully

### As a Merchant
- I want to expose my products in a standard format that agents understand
- I want to control which products are searchable and how they're presented
- I want to highlight product features and competitive advantages
- I want to provide rich metadata (specs, reviews) to help agents sell
- I want to support natural language queries from agents

### As an End User
- I want my agent to find products matching my natural language request
- I want my agent to compare products across merchants (price, features, reviews)
- I want my agent to understand product details (size, color, specifications)
- I want my agent to find alternatives if my preferred product is unavailable
- I want my agent to consider my preferences (brand, price range, ratings)

---

## 5. Proposed Solution

### Architecture Overview

```
User Query: "Find organic coffee under $20"
         ↓
    AI Agent
         ↓
   Product Search API (standardized)
         ↓
   Multiple Merchants (parallel queries)
         ↓
   Unified Product Results
         ↓
   Agent Compares & Filters
         ↓
   Present Options to User
         ↓
   User Selects → ACP Checkout
```

### Core Components

#### 5.1 Product Search Endpoint (Required)
- **Endpoint:** `POST /acp/products/search`
- **Hosted By:** Each merchant
- **Purpose:** Standardized product search across all merchants
- **Authentication:** Bearer token (JWT or OAuth 2.0) - public search may be optional
- **Supports:**
  - Natural language queries
  - Structured filters (category, price range, attributes)
  - Faceted search (filter by multiple attributes)
  - Pagination and sorting
  - Relevance scoring
  - User context for personalized results (when authorized)

#### 5.2 Product Schema (Standardized)
- **Format:** JSON Schema compliant
- **Core Fields:**
  - Product ID, SKU, name, description
  - Pricing (base price, currency, sale price, price history)
  - Availability (in stock, quantity, estimated delivery)
  - Attributes (size, color, material, specifications)
  - Media (images, videos)
  - Ratings and reviews summary
  - Variants and related products
  - Merchant metadata

#### 5.3 Product Detail Endpoint
- **Endpoint:** `GET /acp/products/{product_id}`
- **Purpose:** Retrieve full product details
- **Authentication:** Bearer token (scopes: `products:read`)
- **Returns:** Complete product schema with all metadata

#### 5.4 Product Comparison API
- **Endpoint:** `POST /acp/products/compare`
- **Purpose:** Compare multiple products side-by-side
- **Authentication:** Bearer token (scopes: `products:compare`)
- **Supports:** Cross-merchant comparison
- **Returns:** Normalized comparison matrix

---

## 6. Key Features

### 6.1 Search Capabilities

**Natural Language Search:**
- Agents send natural language queries: "organic coffee beans under $20"
- Merchants return relevant products with relevance scores
- Supports synonyms, typos, and intent understanding

**Structured Search:**
- Category filtering (e.g., "coffee", "electronics")
- Price range filtering
- Attribute filtering (brand, size, color, etc.)
- Availability filtering (in stock, pre-order, etc.)
- Rating filtering (minimum stars)

**Faceted Search:**
- Merchants return available facets (price ranges, brands, attributes)
- Agents can refine searches iteratively
- Supports multi-select filters

### 6.2 Product Data Standardization

**Core Product Fields:**
```json
{
  "product_id": "prod_abc123",
  "sku": "COFFEE-001",
  "name": "Organic Colombian Coffee Beans",
  "description": "Premium single-origin...",
  "category": ["coffee", "organic", "beans"],
  "brand": "Coffee Co.",
  "merchant_id": "merchant_xyz"
}
```

**Pricing:**
```json
{
  "base_price": {
    "amount": 1899,
    "currency": "USD",
    "formatted": "$18.99"
  },
  "sale_price": {
    "amount": 1499,
    "currency": "USD",
    "formatted": "$14.99"
  },
  "price_valid_until": "2026-02-01T00:00:00Z"
}
```

**Availability:**
```json
{
  "in_stock": true,
  "quantity": 45,
  "availability_status": "in_stock",
  "estimated_delivery": {
    "min_days": 2,
    "max_days": 5,
    "shipping_method": "standard"
  }
}
```

**Attributes:**
```json
{
  "attributes": {
    "weight": "12 oz",
    "roast_level": "medium",
    "origin": "Colombia",
    "certifications": ["organic", "fair_trade"]
  }
}
```

### 6.3 Product Relationships

**Variants:**
- Products with multiple options (size, color)
- Variants share core attributes but differ in specific fields
- Agents can present variant selection to users

**Bundles:**
- Products sold together at a discount
- Merchants specify bundle composition and savings

**Alternatives:**
- Similar products that might interest users
- Merchants suggest alternatives (upgrades, different brands)

**Related Products:**
- Complementary items (e.g., coffee filters for coffee makers)
- Frequently bought together suggestions

### 6.4 Rich Metadata

**Ratings & Reviews:**
- Aggregate ratings (average stars, review count)
- Review summaries (pros, cons, common themes)
- Review distribution (5-star breakdown)

**Specifications:**
- Technical specs for electronics, appliances
- Dimensions, weight, materials
- Compatibility information

**Media:**
- Product images (multiple angles, zoom)
- Videos (product demos, reviews)
- 360-degree views (if available)

---

## 7. Technical Considerations

### 7.1 Search API Specification

**Request:**
```json
{
  "query": "organic coffee under $20",
  "filters": {
    "category": ["coffee"],
    "price_range": {
      "min": 0,
      "max": 2000,
      "currency": "USD"
    },
    "attributes": {
      "organic": true
    },
    "availability": "in_stock",
    "min_rating": 4
  },
  "sort": "relevance", // or "price_asc", "price_desc", "rating", "newest"
  "pagination": {
    "page": 1,
    "per_page": 20
  },
  "include_facets": true
}
```

**Response:**
```json
{
  "products": [
    {
      "product_id": "prod_abc123",
      "name": "Organic Colombian Coffee",
      "base_price": { "amount": 1899, "currency": "USD" },
      "sale_price": { "amount": 1499, "currency": "USD" },
      "availability": { "in_stock": true, "quantity": 45 },
      "rating": { "average": 4.5, "count": 127 },
      "image_url": "https://...",
      "relevance_score": 0.92
    }
  ],
  "facets": {
    "price_ranges": [
      { "min": 0, "max": 1000, "count": 12 },
      { "min": 1000, "max": 2000, "count": 8 }
    ],
    "brands": [
      { "name": "Coffee Co.", "count": 5 },
      { "name": "Bean Co.", "count": 3 }
    ]
  },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "total_pages": 3
  },
  "search_metadata": {
    "query_time_ms": 145,
    "merchant_id": "merchant_xyz"
  }
}
```

### 7.2 Product Detail API

**Request:**
```
GET /acp/products/prod_abc123?include=variants,reviews,specifications
```

**Response:**
```json
{
  "product_id": "prod_abc123",
  "sku": "COFFEE-001",
  "name": "Organic Colombian Coffee Beans",
  "description": "Premium single-origin...",
  "category": ["coffee", "organic", "beans"],
  "brand": "Coffee Co.",
  "pricing": { /* full pricing details */ },
  "availability": { /* full availability details */ },
  "attributes": { /* all attributes */ },
  "images": [
    { "url": "...", "alt": "Front view", "type": "primary" },
    { "url": "...", "alt": "Side view", "type": "secondary" }
  ],
  "rating": {
    "average": 4.5,
    "count": 127,
    "distribution": { "5": 80, "4": 30, "3": 10, "2": 5, "1": 2 }
  },
  "variants": [
    {
      "variant_id": "var_001",
      "attributes": { "size": "12 oz" },
      "pricing": { "amount": 1499, "currency": "USD" },
      "availability": { "in_stock": true }
    }
  ],
  "related_products": [ /* product IDs */ ],
  "specifications": {
    "weight": "12 oz",
    "roast_level": "medium",
    "origin": "Colombia"
  }
}
```

### 7.3 Comparison API

**Request:**
```json
{
  "product_ids": [
    "merchant_abc:prod_123",
    "merchant_xyz:prod_456",
    "merchant_def:prod_789"
  ],
  "compare_fields": ["price", "rating", "availability", "attributes"]
}
```

**Response:**
```json
{
  "comparison": {
    "products": [ /* normalized product data */ ],
    "differences": {
      "price": {
        "lowest": "merchant_xyz:prod_456",
        "highest": "merchant_def:prod_789",
        "difference": 500
      },
      "rating": {
        "highest": "merchant_abc:prod_123",
        "lowest": "merchant_def:prod_789"
      }
    },
    "common_attributes": ["organic", "fair_trade"],
    "unique_attributes": {
      "merchant_abc:prod_123": ["single_origin"],
      "merchant_xyz:prod_456": ["bulk_discount"]
    }
  }
}
```

### 7.4 Caching & Performance

**Caching Strategy:**
- Product search results: 5-15 minutes TTL (depending on merchant)
- Product details: 1-5 minutes TTL
- Facets: 15-30 minutes TTL
- Merchants specify cache headers (Cache-Control, ETag)

**Performance Requirements:**
- Search API: <500ms p95 response time
- Product detail: <200ms p95 response time
- Support for pagination to handle large result sets
- Rate limiting: Merchants specify limits in capabilities

**Optimization:**
- Agents can request lightweight product summaries for lists
- Full details fetched only when needed
- Support for batch product detail requests

### 7.5 Authentication & Authorization

#### 7.5.1 Authentication Model

**Agent Authentication:**
- Agents authenticate using **Bearer tokens** (JWT or OAuth 2.0 access tokens)
- Tokens issued by ACP-compatible identity providers or merchant-specific auth systems
- Token format: `Authorization: Bearer <token>` header on all requests
- Token validation: Merchants validate tokens before processing requests

**Token Types:**
1. **Public Search Tokens** (Optional):
   - Allow unauthenticated or lightly authenticated product browsing
   - Limited to public product data (no personalized pricing, limited inventory details)
   - Rate-limited more aggressively
   - Use case: Initial product discovery before user authentication

2. **Agent-Scoped Tokens**:
   - Issued to specific AI agents/platforms (e.g., ChatGPT, Claude)
   - Identifies the agent making the request
   - Allows merchants to track agent usage and apply agent-specific policies
   - Includes agent metadata: `agent_id`, `agent_platform`, `agent_version`

3. **User-Delegated Tokens**:
   - Issued on behalf of authenticated end users
   - Enables personalized search results, user-specific pricing, purchase history
   - Includes user context: `user_id`, `user_preferences`, `shipping_address`
   - Required for checkout flow integration

**Token Structure Example:**
```json
{
  "iss": "https://acp-auth.example.com",
  "sub": "agent_chatgpt_001",
  "aud": "merchant_xyz",
  "exp": 1735689600,
  "iat": 1735603200,
  "agent_id": "chatgpt_001",
  "agent_platform": "OpenAI",
  "user_id": "user_abc123", // Optional, for user-delegated tokens
  "scopes": ["products:read", "products:search"],
  "merchant_id": "merchant_xyz"
}
```

#### 7.5.2 Authorization & Scopes

**Permission Scopes:**
- `products:read` - Read product details (public data)
- `products:search` - Search products catalog
- `products:compare` - Compare products across merchants
- `products:personalized` - Access personalized pricing and recommendations (requires user context)
- `products:inventory` - Access detailed inventory information
- `products:reviews` - Access full review data (not just summaries)

**Scope-Based Access Control:**
- Merchants can restrict certain product data based on scopes
- Public tokens: Limited to `products:read` and `products:search` with public data only
- Agent tokens: Can include `products:compare` and `products:inventory`
- User-delegated tokens: Full access including `products:personalized`

**Authorization Flow:**
```
1. Agent requests token from identity provider
   ↓
2. Identity provider validates agent credentials
   ↓
3. Token issued with appropriate scopes
   ↓
4. Agent includes token in API requests
   ↓
5. Merchant validates token and checks scopes
   ↓
6. Merchant returns data based on authorized scopes
```

#### 7.5.3 User Consent & Delegation

**User Authorization:**
- Users must explicitly authorize agents to search products on their behalf
- Authorization can be:
  - **Session-based**: Valid for current session only
  - **Persistent**: Stored for future sessions (with user consent)
  - **Scope-limited**: User can restrict what agents can access

**Delegation Mechanism:**
- Users grant permissions through OAuth 2.0 authorization flow
- Agents request specific scopes: `products:search`, `products:read`, `checkout:create`
- Users can approve/deny individual scopes
- Authorization can be revoked at any time

**User Context in Requests:**
```json
{
  "query": "organic coffee",
  "user_context": {
    "user_id": "user_abc123",
    "shipping_address": {
      "country": "US",
      "postal_code": "10001"
    },
    "preferences": {
      "price_range": { "max": 2000 },
      "preferred_brands": ["Coffee Co."]
    }
  },
  "authorization": {
    "token": "Bearer eyJ...",
    "scopes": ["products:search", "products:personalized"]
  }
}
```

#### 7.5.4 Merchant-Side Authorization

**Merchant Authorization Policies:**
- Merchants can implement their own authorization rules:
  - **Whitelist agents**: Only allow specific verified agents
  - **Rate limiting**: Different limits for different agent types
  - **Data filtering**: Restrict certain products/categories based on agent
  - **Geographic restrictions**: Limit product visibility by user location

**Agent Verification:**
- Merchants can verify agent identity through:
  - Token issuer validation (trusted identity providers)
  - Agent registry lookup (via Merchant Discovery Protocol)
  - Certificate pinning for high-security scenarios

**Authorization Response Codes:**
- `200 OK` - Request authorized, data returned
- `401 Unauthorized` - Invalid or missing token
- `403 Forbidden` - Token valid but insufficient scopes
- `429 Too Many Requests` - Rate limit exceeded

#### 7.5.5 Security Considerations

**Token Security:**
- Tokens must be transmitted over HTTPS only
- Short-lived tokens (15-60 minutes) with refresh mechanism
- Token rotation on refresh to prevent replay attacks
- Revocation support for compromised tokens

**Privacy Protection:**
- User data in tokens should be minimal (user_id only, not PII)
- Merchants should not log full user context in search queries
- Personalization data should be encrypted in transit
- User consent must be auditable

**Rate Limiting:**
- Public tokens: Stricter limits (e.g., 100 requests/hour)
- Agent tokens: Moderate limits (e.g., 1000 requests/hour)
- User-delegated tokens: Higher limits (e.g., 5000 requests/hour)
- Rate limits specified in merchant capabilities endpoint

**Audit & Logging:**
- Merchants should log:
  - Agent identity (agent_id, platform)
  - Request type (search, detail, compare)
  - Authorization result (success/failure)
  - Rate limit status
- User PII should NOT be logged in search queries
- Logs retained for security/compliance purposes only

#### 7.5.6 Implementation Examples

**Public Search (No Authentication):**
```http
POST /acp/products/search HTTP/1.1
Host: merchant.example.com
Content-Type: application/json

{
  "query": "coffee",
  "filters": { "category": ["coffee"] }
}
```

**Agent-Authenticated Search:**
```http
POST /acp/products/search HTTP/1.1
Host: merchant.example.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "query": "organic coffee",
  "filters": { "category": ["coffee"], "availability": "in_stock" },
  "agent_metadata": {
    "agent_id": "chatgpt_001",
    "platform": "OpenAI"
  }
}
```

**User-Delegated Search:**
```http
POST /acp/products/search HTTP/1.1
Host: merchant.example.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "query": "coffee under $20",
  "user_context": {
    "user_id": "user_abc123",
    "shipping_address": { "country": "US", "postal_code": "10001" }
  },
  "scopes": ["products:search", "products:personalized"]
}
```

---

## 8. Success Metrics

### Adoption Metrics
- **80%+ of ACP merchants** implement product search endpoint within 6 months
- **90%+ of agent transactions** use standardized product search
- **50+ product categories** with standardized schemas

### Performance Metrics
- **<500ms** average search response time (p95)
- **<200ms** product detail response time (p95)
- **99.9%** API uptime for merchants
- **<2%** error rate on product searches

### User Experience Metrics
- **80%+ search relevance** (products match user intent)
- **60%+ comparison accuracy** (agents correctly compare products)
- **Reduced checkout abandonment** (better product discovery)

### Business Metrics
- **Increased conversion rates** (better product matching)
- **Higher average order value** (better product discovery)
- **Reduced support queries** (clearer product information)

---

## 9. Implementation Phases

### Phase 1: Core Search (Months 1-2)
- Define product schema specification
- Implement basic search endpoint (`/acp/products/search`)
- Support natural language and structured queries
- Basic filtering (category, price, availability)
- Product detail endpoint
- 10-20 pilot merchants

### Phase 2: Enhanced Search (Months 3-4)
- Faceted search support
- Product variants and relationships
- Rich metadata (ratings, reviews, specifications)
- Comparison API
- Advanced filtering (attributes, ratings, brands)
- 50+ merchants onboarded

### Phase 3: Optimization (Months 5-6)
- Search relevance improvements
- Performance optimization
- Caching strategies
- Batch operations
- Multi-language support
- 100+ merchants

---

## 10. Open Questions

1. **Taxonomy:** Should ACP define a standard product category taxonomy, or allow merchants to use their own?
2. **Search Quality:** How do we ensure merchants provide high-quality search results? Any minimum requirements?
3. **Pricing:** Should merchants expose price history, or just current pricing?
4. **Inventory:** How granular should inventory information be? Real-time vs. approximate?
5. **Internationalization:** How to handle multi-language product names and descriptions?
6. **Product Updates:** Should merchants push product updates, or agents poll?
7. **Image Standards:** Minimum image requirements? Format standards?
8. **Review Integration:** Should reviews be embedded in product data, or separate API?
9. **Merchant-Specific Fields:** How to handle merchant-specific attributes while maintaining standardization?
10. **Search Ranking:** Should merchants control ranking, or is it purely relevance-based?
11. **Authentication:** Should public product search require authentication, or be optional for basic discovery?
12. **Token Issuance:** Who issues tokens? Centralized ACP identity provider or merchant-specific?
13. **User Consent:** How granular should user consent be? Per-session or persistent?
14. **Agent Verification:** Should merchants verify agents through a central registry, or trust token issuers?

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Merchants implement search inconsistently | High | Clear schema spec, validation tools, reference implementation |
| Poor search quality hurts user experience | High | Relevance guidelines, quality metrics, merchant feedback |
| Performance issues with large catalogs | Medium | Pagination, caching, performance requirements |
| Product data becomes stale | Medium | Cache TTLs, freshness indicators, update mechanisms |
| Schema evolution breaks agents | Medium | Versioning strategy, backward compatibility, deprecation process |
| Low merchant adoption | High | Clear value proposition, easy implementation, reference code |
| Search spam or manipulation | Medium | Rate limiting, quality guidelines, monitoring |

---

## 12. Dependencies

- **ACP Checkout Spec:** Product search feeds into checkout flow
- **Merchant Discovery Protocol:** Agents discover merchants, then search products
- **Payment Providers:** May need pricing/currency standardization
- **Schema Standards:** JSON Schema for product data validation

---

## 13. Future Enhancements (Post-v1)

- **Visual Search:** Search products by image (find similar products)
- **Voice Search:** Optimized for voice-based agent queries
- **Personalization:** User preference-based search results
- **Predictive Search:** Anticipate user needs based on context
- **Multi-Merchant Aggregation:** Unified search across all merchants
- **Product Bundling:** Agents suggest product bundles across merchants
- **Price Tracking:** Historical price data and price drop alerts
- **Inventory Alerts:** Notify agents when out-of-stock items become available
- **Product Recommendations:** ML-based recommendations (merchant-provided or agent-computed)

---

## 14. Conclusion

The Product Search & Catalog Protocol addresses a critical gap in the ACP ecosystem by standardizing how agents discover and evaluate products. This will:

- **Enable intelligent product discovery** across the entire ACP merchant ecosystem
- **Reduce integration complexity** for both agents and merchants
- **Improve user experience** through better product matching and comparison
- **Accelerate ACP adoption** by making it easier for merchants to participate

This protocol complements the Merchant Discovery Protocol perfectly: merchants are discovered first, then products are searched within those merchants. Together, they create a complete discovery-to-purchase flow.

Recommended next step: **Socialize this PRD with ACP maintainers** and gather feedback from merchant and agent developer communities before drafting technical RFC and OpenAPI specifications.

