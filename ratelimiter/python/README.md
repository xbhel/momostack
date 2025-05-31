# Rate Limiter

## References

- [SystemDesign: Distributed API Rate Limiter](https://systemsdesign.cloud/SystemDesign/RateLimiter)
- [Google-architecture: Rate-limiting strategies and techniques](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
- [Cloudflare: What is rate limiting?](https://www.cloudflare.com/learning/bots/what-is-rate-limiting/)
- [Cloudflare: How we built rate limiting capable of scaling to millions of domains](https://blog.cloudflare.com/counting-things-a-lot-of-different-things/)
- [NGINX Rate Limiting](https://www.nginx.com/blog/rate-limiting-nginx/)
- [Guava Rate Limiter](https://github.com/google/guava/blob/master/guava/src/com/google/common/util/concurrent/RateLimiter.java)
- [Guava Rate Limiter Test](https://github.com/google/guava/blob/master/guava-tests/test/com/google/common/util/concurrent/RateLimiterTest.java)
- [Quick Guide to the Guava RateLimiter](https://www.baeldung.com/guava-rate-limiter)


## What is Rate Limiting?

Rate limiting are a way to limit the number of requests that can be made to a specific endpoint. This is useful for preventing abuse of your API. For example, you may want to limit the number of requests that can be made to your endpoint to prevent brute force attacks. They also prevent resource starvation by limiting the number of requests that can be made to a specific endpoint. 

An API that utilizes rate limiting may throttle clients that attempt to make too many calls or temporarily block them altogether. Users who have been throttled may either have their requests denied or slowed down for a set time. This will allow legitimate requests to still be fulfilled without slowing down the entire application.

API responses with HTTP Status Code **429 Too Many Requests** when a request is rate limited or throttled.


## Rate Limiting vs Throttling

Rate Limiting is a process that is used to define the rate and speed at which consumers can access APIs. Throttling is the process of controlling the usage of the APIs by customers during a given period. Throttling can be defined at the application level and/or API level. When a throttle limit is crossed, the server returns HTTP status "429 - Too many requests".


## Where to put the Rate Limiter ?

1. **Server side**: This is the least common type of rate limiters. Server side rate limiters are more effective than client side rate limiters. They can not be bypassed by using multiple clients. They also protect the server from malicious users.

2. **Client side**: This is the most common type of rate limiter. Client side rate limiters are easy to implement, but they are not very effective. Malicious actor can change client-side code and bypass rate limiter. 

3. **Proxy**: There is third and much better option to implement rate limiter as middleware. (It is an easier way in a distributed system.)

![Request limiter implemented in API Gateway](../../../docs/.assets/rate-limiting-client-side.png)

### Server-side Strategies

There are several major types of rate limiting models that a business can choose between depending on which one offers the best fit for a business based on the nature of the web services that they offer, as we will explore in greater detail below.

- User-Level Rate Limiting: In cases where a system can uniquely identify a user, it can restrict the number of API requests that a user makes in a time period. For example, if the user is only allowed to make two requests per second, the system denies the user’s third request made in the same second. User-level rate limiting ensures fair usage. However, maintaining the usage statistics of each user can create an overhead to the system that if not required for other reasons, could be a drain on resources.

- Server-Level Rate Limiting: Most API-based services are distributed in nature. That means when a user sends a request, it might be serviced by any one of the many servers. In distributed systems, rate limiting can be used for load-sharing among servers. For example, if one server receives a large chunk of requests out of ten servers in a distributed system and others are mostly idle, the system is not fully utilized. There will be a restriction on the number of service requests that a particular server can handle in server-level rate limiting. If a server receives requests that are over this set limit, they are either dropped or routed to another server. Server-level rate limiting ensures the system’s availability and prevents denial of service attacks targeted at a particular server.

- Geography-Based Rate Limiting: Most API-based services have servers spread across the globe. When a user issues an API request, a server close to the user’s geographic location fulfils it. Organizations implement geography-based rate limiting to restrict the number of service requests from a particular geographic area. This can also be done based on timing. For example, if the number of requests coming from a particular geographic location is small from 1:00 am to 6:00 am, then a web server can have a rate limiting rule for this particular period. If there is an attack on the server during these hours, the number of requests will spike. In the event of a spike, the rate limiting mechanism will then trigger an alert and the organization can quickly respond to such an attack.

### Client-side Strategies

The strategies described so far apply to rate limiting on the server side. However, these strategies can inform the design of clients, especially when you consider that many components in a distributed system are both client and server.

Just as a service's primary purpose in using rate limiting is to protect itself and maintain availability, a client's primary purpose is to fulfill the request it is making to a service. A service might be unable to fulfill a request from a client for a variety of reasons, including the following:
- The service is unreachable because of network conditions.
- The service returned a non-specific error.
- The service denies the request because of an authentication or authorization failure.
- The client request is invalid or malformed.
- <u>The service rate-limits the caller and sends a back-pressure signal (commonly a 429 response).</u> (**xbhel: this is what I'm facing.**)


## Common Rate Limiting Algorithms

- Token Bucket algorithm
- Leaky Bucket algorithm
- Fixed Window Counter algorithm
- Sliding Window Logs algorithm
- Sliding Window Counter algorithm

### Token Bucket Algorithm

The Token Bucket algorithm works as follows: 

1. Define a token bucket which is a container that has pre-defined capacity.
2. Tokens are put in the bucket(refill into the bucket) at preset rates periodically. Once the bucket is full, no more tokens are add.
3. When a request arrived, a token is removed from the bucket.
4. If there are no tokens in the bucket, the request will be dropped and False will return.

Here's a Python implementation of the Token Bucket Algorithm: 

- [*Python-Token-Bucket-Rate-Limiter.py*](./src/ratelimiter.py)
- [Tests for Python-Token-Bucket-Rate-Limiter.py](./tests/unit/test_ratelimiter.py)



