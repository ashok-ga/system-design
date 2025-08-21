# LLD Systems — Consolidated Specs & Code

This Markdown bundles the original comment specs and full Java implementations for multiple LLD exercises, each in its own section.

## Table of Contents

1. [Parking Lot](#parking-lot)
2. [Movie Booking](#movie-booking)
3. [Food Delivery](#food-delivery)
4. [Ride Sharing](#ride-sharing)
5. [Chat App](#chat-app)
6. [File Store](#file-store)
7. [Instagram Feed](#instagram-feed)
8. [Meeting Scheduler](#meeting-scheduler)

## Parking Lot

```
/*
Template ->
1) define functional requirements
   - Single lot with levels, slots typed by vehicle (BIKE/CAR).
   - Entry: allocate nearest free slot by type, create ticket.
   - Exit: compute fee (base + hourly rounded up), release slot.
   - Query: availability per level & type.
   - Keep it concurrency-safe (basic locking), in-memory only.

2) define entities / actors
   Actors: Driver, Gate (Entry/Exit)
   Entities: Lot, Level, Slot(OPEN/OCCUPIED/MAINTENANCE, vehicleType), Ticket(OPEN/CLOSED), PricingRule

3) define apis - get/post/put, request, response
   GET  /availability?lotId=... -> { levelId -> {CAR:n, BIKE:n} }
   POST /entry                  {lotId, gateId, vehicleType, plate} -> {ticketId, slotId, entryAt}
   POST /exit                   {ticketId} -> {amount, exitAt, status}
   (Implemented as method calls in the Controller facade)

4) define services involved
   SlotService   - allocate/release slots (nearest level first)
   TicketService - issue/close tickets, orchestrates pricing + slot ops
   PricingService- compute amount (base + hourly)
   AvailabilityService - compute free counts excluding OCCUPIED/MAINTENANCE

5) define db schema - what all tables are required, what are the columns, what are the keys
   (In-memory for interview; relational sketch)
   lot(id PK, name, tz)
   level(id PK, lot_id FK, idx, name)
   slot(id PK, level_id FK, code UNIQUE(level_id, code), vehicle_type, status)
   pricing_rule(id PK, lot_id FK, vehicle_type, base_fee, hourly_rate)
   ticket(id PK, lot_id FK, slot_id FK, vehicle_type, plate, entry_at, exit_at, amount, status)
*/
```

### Java Implementation

```java
/*
Template ->
1) define functional requirements
   - Single lot with levels, slots typed by vehicle (BIKE/CAR).
   - Entry: allocate nearest free slot by type, create ticket.
   - Exit: compute fee (base + hourly rounded up), release slot.
   - Query: availability per level & type.
   - Keep it concurrency-safe (basic locking), in-memory only.

2) define entities / actors
   Actors: Driver, Gate (Entry/Exit)
   Entities: Lot, Level, Slot(OPEN/OCCUPIED/MAINTENANCE, vehicleType), Ticket(OPEN/CLOSED), PricingRule

3) define apis - get/post/put, request, response
   GET  /availability?lotId=... -> { levelId -> {CAR:n, BIKE:n} }
   POST /entry                  {lotId, gateId, vehicleType, plate} -> {ticketId, slotId, entryAt}
   POST /exit                   {ticketId} -> {amount, exitAt, status}
   (Implemented as method calls in the Controller facade)

4) define services involved
   SlotService   - allocate/release slots (nearest level first)
   TicketService - issue/close tickets, orchestrates pricing + slot ops
   PricingService- compute amount (base + hourly)
   AvailabilityService - compute free counts excluding OCCUPIED/MAINTENANCE

5) define db schema - what all tables are required, what are the columns, what are the keys
   (In-memory for interview; relational sketch)
   lot(id PK, name, tz)
   level(id PK, lot_id FK, idx, name)
   slot(id PK, level_id FK, code UNIQUE(level_id, code), vehicle_type, status)
   pricing_rule(id PK, lot_id FK, vehicle_type, base_fee, hourly_rate)
   ticket(id PK, lot_id FK, slot_id FK, vehicle_type, plate, entry_at, exit_at, amount, status)
*/

import java.time.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/* ===== Domain ===== */
enum VehicleType { BIKE, CAR }
enum SlotStatus   { OPEN, OCCUPIED, MAINTENANCE }
enum TicketStatus { OPEN, CLOSED }

final class Lot { final String id, name; final ZoneId zone; Lot(String i,String n,ZoneId z){id=i;name=n;zone=z;} }
final class Level { final String id, lotId, name; final int idx; Level(String i,String l,String n,int x){id=i;lotId=l;name=n;idx=x;} }
final class Slot {
    final String id, levelId, code; final VehicleType type; volatile SlotStatus status=SlotStatus.OPEN;
    Slot(String i,String lvl,String c,VehicleType t){id=i;levelId=lvl;code=c;type=t;}
}
final class PricingRule {
    final String id, lotId; final VehicleType type; final double baseFee, hourlyRate;
    PricingRule(String i,String l,VehicleType t,double b,double h){id=i;lotId=l;type=t;baseFee=b;hourlyRate=h;}
}
final class Ticket {
    final String id, lotId, slotId, plate; final VehicleType type; final Instant entryAt;
    volatile Instant exitAt; volatile Double amount; volatile TicketStatus status=TicketStatus.OPEN;
    Ticket(String i,String l,String s,VehicleType t,String p,Instant e){id=i;lotId=l;slotId=s;type=t;plate=p;entryAt=e;}
}

/* ===== Simple Repos (in-memory) ===== */
class Ids { private final AtomicLong seq=new AtomicLong(1); String next(String p){return p+"-"+seq.getAndIncrement();} }
class LotsRepo { final Map<String,Lot> m=new ConcurrentHashMap<>(); Lot save(Lot x){m.put(x.id,x);return x;} Optional<Lot> byId(String id){return Optional.ofNullable(m.get(id));} }
class LevelsRepo { final Map<String,Level> m=new ConcurrentHashMap<>(); Level save(Level x){m.put(x.id,x);return x;} List<Level> byLot(String lotId){return m.values().stream().filter(a->a.lotId.equals(lotId)).sorted(Comparator.comparingInt(a->a.idx)).collect(Collectors.toList());} }
class SlotsRepo {
    final Map<String,Slot> m=new ConcurrentHashMap<>();
    Slot save(Slot x){m.put(x.id,x);return x;}
    Optional<Slot> byId(String id){return Optional.ofNullable(m.get(id));}
    List<Slot> byLevel(String levelId){return m.values().stream().filter(s->s.levelId.equals(levelId)).collect(Collectors.toList());}
}
class PricingRepo {
    final Map<String,PricingRule> m=new ConcurrentHashMap<>();
    PricingRule save(PricingRule p){m.put(p.id,p);return p;}
    Optional<PricingRule> byLotType(String lotId, VehicleType t){return m.values().stream().filter(r->r.lotId.equals(lotId)&&r.type==t).findFirst();}
}
class TicketsRepo {
    final Map<String,Ticket> m=new ConcurrentHashMap<>();
    Ticket save(Ticket t){m.put(t.id,t);return t;}
    Optional<Ticket> byId(String id){return Optional.ofNullable(m.get(id));}
}

/* ===== Exceptions ===== */
class DomainException extends RuntimeException { DomainException(String m){super(m);} }

/* ===== Services ===== */
class PricingService {
    private final PricingRepo pricing; private final LotsRepo lots;
    PricingService(PricingRepo p, LotsRepo l){pricing=p;lots=l;}
    double compute(String lotId, VehicleType type, Instant entry, Instant exit){
        PricingRule r = pricing.byLotType(lotId, type).orElseThrow(()->new DomainException("pricing missing"));
        long secs = Math.max(0, Duration.between(entry, exit).getSeconds());
        long hrs = (secs==0)?0:((secs+3599)/3600); // round up started hour
        double total = r.baseFee + r.hourlyRate * hrs;
        return Math.round(total*100.0)/100.0;
    }
}
class SlotService {
    private final SlotsRepo slots; private final LevelsRepo levels;
    SlotService(SlotsRepo s, LevelsRepo l){slots=s;levels=l;}
    synchronized Slot allocateNearest(String lotId, VehicleType type){
        for (Level lvl: levels.byLot(lotId)){
            for (Slot s: slots.byLevel(lvl.id)){
                if (s.type==type && s.status==SlotStatus.OPEN){
                    s.status=SlotStatus.OCCUPIED; return slots.save(s);
                }
            }
        }
        throw new DomainException("no free slot");
    }
    synchronized void release(String slotId){
        Slot s = slots.byId(slotId).orElseThrow(()->new DomainException("slot not found"));
        s.status=SlotStatus.OPEN; slots.save(s);
    }
}
class TicketService {
    private final TicketsRepo tickets; private final SlotService slotSvc; private final PricingService pricingSvc; private final Ids ids;
    TicketService(TicketsRepo t, SlotService s, PricingService p, Ids ids){tickets=t;slotSvc=s;pricingSvc=p;this.ids=ids;}
    Ticket entry(String lotId, VehicleType type, String plate){
        Slot s = slotSvc.allocateNearest(lotId, type);
        Ticket t = new Ticket(ids.next("tkt"), lotId, s.id, type, plate, Instant.now());
        return tickets.save(t);
    }
    Ticket exit(String ticketId){
        Ticket t = tickets.byId(ticketId).orElseThrow(()->new DomainException("ticket not found"));
        if (t.status==TicketStatus.CLOSED) return t;
        t.exitAt = Instant.now();
        t.amount = pricingSvc.compute(t.lotId, t.type, t.entryAt, t.exitAt);
        t.status = TicketStatus.CLOSED;
        tickets.save(t);
        slotSvc.release(t.slotId);
        return t;
    }
}
class AvailabilityService {
    private final LevelsRepo levels; private final SlotsRepo slots;
    AvailabilityService(LevelsRepo l, SlotsRepo s){levels=l;slots=s;}
    Map<String, Map<VehicleType,Integer>> availability(String lotId){
        Map<String,Map<VehicleType,Integer>> out = new LinkedHashMap<>();
        for (Level lvl: levels.byLot(lotId)){
            EnumMap<VehicleType,Integer> m = new EnumMap<>(VehicleType.class);
            for (VehicleType vt: VehicleType.values()) m.put(vt,0);
            for (Slot s: slots.byLevel(lvl.id)){
                if (s.status==SlotStatus.OPEN) m.compute(s.type,(k,v)->v+1);
            }
            out.put(lvl.name, m);
        }
        return out;
    }
}

/* ===== Controller (facade mirroring APIs) ===== */
class ParkingController {
    private final AvailabilityService avail; private final TicketService tickets;
    ParkingController(AvailabilityService a, TicketService t){avail=a;tickets=t;}
    Map<String, Map<VehicleType,Integer>> getAvailability(String lotId){ return avail.availability(lotId); }
    Ticket postEntry(String lotId, VehicleType type, String plate){ return tickets.entry(lotId, type, plate); }
    Ticket postExit(String ticketId){ return tickets.exit(ticketId); }
}

/* ===== Bootstrap / Demo (kept tiny for 40-min scope) ===== */
public class ParkingLot40Min {
    public static void main(String[] args) {
        Ids ids = new Ids();
        // Repos
        LotsRepo lots = new LotsRepo();
        LevelsRepo levels = new LevelsRepo();
        SlotsRepo slots = new SlotsRepo();
        PricingRepo pricing = new PricingRepo();
        TicketsRepo tickets = new TicketsRepo();

        // Seed a small lot
        Lot lot = lots.save(new Lot("LOT-1","HSR Central", ZoneId.of("Asia/Kolkata")));
        Level L0 = levels.save(new Level("L0","LOT-1","Ground",0));
        Level L1 = levels.save(new Level("L1","LOT-1","P1",1));
        // Few slots
        slots.save(new Slot("S1","L0","C-001",VehicleType.CAR));
        slots.save(new Slot("S2","L0","C-002",VehicleType.CAR));
        slots.save(new Slot("S3","L1","B-001",VehicleType.BIKE));
        // Pricing
        pricing.save(new PricingRule("PR-CAR","LOT-1",VehicleType.CAR,  20.0, 30.0));
        pricing.save(new PricingRule("PR-BIKE","LOT-1",VehicleType.BIKE, 10.0, 10.0));

        // Services + Controller
        PricingService pricingSvc = new PricingService(pricing, lots);
        SlotService slotSvc = new SlotService(slots, levels);
        TicketService ticketSvc = new TicketService(tickets, slotSvc, pricingSvc, ids);
        AvailabilityService av = new AvailabilityService(levels, slots);
        ParkingController api = new ParkingController(av, ticketSvc);

        // --- Demo as API calls ---
        System.out.println("GET /availability -> " + api.getAvailability("LOT-1"));
        Ticket t1 = api.postEntry("LOT-1", VehicleType.CAR, "KA-01-AB-1234");
        System.out.println("POST /entry -> " + t1.id + " slot=" + t1.slotId);
        System.out.println("GET /availability -> " + api.getAvailability("LOT-1"));
        sleep(1200); // simulate time
        Ticket closed = api.postExit(t1.id);
        System.out.println("POST /exit -> ticket=" + closed.id + " amount=" + closed.amount);
        System.out.println("GET /availability -> " + api.getAvailability("LOT-1"));
    }
    private static void sleep(long ms){ try{ Thread.sleep(ms);}catch(Exception ignored){} }
}
```

## Movie Booking

```
/*
Template ->
1) define functional requirements
   - Browse shows for a movie in a city & date.
   - View seat map for a show: FREE / HELD (by TTL hold) / BOOKED.
   - Hold seats with TTL (e.g., 5 minutes). Holds block others but auto-expire on read.
   - Confirm booking from a valid hold; mark seats BOOKED; compute price.
   - Confirm payment (stub), return e-ticket code.
   - In-memory only, concurrency-safe per Show (locks). Keep it 40-min friendly.

2) define entities / actors
   Actors: User, System (Seat Inventory), Payment Gateway (stub)
   Entities: Movie, Theater, Screen, Seat, Show, SeatHold, Booking, Payment

3) define apis - get/post/put, request, response
   GET  /movies/{movieId}/shows?city=...&date=YYYY-MM-DD
        -> [{showId, theater, screen, startAt, basePrice}]
   GET  /shows/{showId}/seats
        -> { showId, seats: [{seatId,row,col,type,status:FREE|HELD|BOOKED}], holdTtlSec }
   POST /shows/{showId}/hold
        { userId, seatIds:[...], ttlSec }
        -> { holdId, expiresAt }
   POST /bookings
        { holdId, userId }
        -> { bookingId, amount, seats:[...], qr }
   POST /payments/confirm
        { bookingId, method, txnRef? }
        -> { paymentId, status }

4) define services involved
   ShowSearchService     - list shows for movie/city/date.
   SeatInventoryService  - seat map, create hold (per-show lock), check expiries.
   BookingService        - confirm booking from hold (per-show lock), pricing.
   PaymentService        - stub payment confirmation.
   IdGenerator           - simple IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   movie(id PK, title, duration_min)
   theater(id PK, city, name)
   screen(id PK, theater_id FK, name, rows, cols)
   seat(id PK, screen_id FK, row, col, type ENUM)
   show(id PK, movie_id FK, screen_id FK, start_at, base_price NUM, status)
   seat_hold(id PK, show_id FK, user_id, seat_ids JSON, expires_at, active)
      INDEX(show_id, active, expires_at)
   booking(id PK, show_id FK, user_id, seat_ids JSON, amount NUM, status, qr)
      INDEX(show_id, status)
   payment(id PK, booking_id FK UNIQUE, method, amount NUM, status, txn_ref, paid_at)
*/
```

### Java Implementation

```java
/*
Template ->
1) define functional requirements
   - Browse shows for a movie in a city & date.
   - View seat map for a show: FREE / HELD (by TTL hold) / BOOKED.
   - Hold seats with TTL (e.g., 5 minutes). Holds block others but auto-expire on read.
   - Confirm booking from a valid hold; mark seats BOOKED; compute price.
   - Confirm payment (stub), return e-ticket code.
   - In-memory only, concurrency-safe per Show (locks). Keep it 40-min friendly.

2) define entities / actors
   Actors: User, System (Seat Inventory), Payment Gateway (stub)
   Entities: Movie, Theater, Screen, Seat, Show, SeatHold, Booking, Payment

3) define apis - get/post/put, request, response
   GET  /movies/{movieId}/shows?city=...&date=YYYY-MM-DD
        -> [{showId, theater, screen, startAt, basePrice}]
   GET  /shows/{showId}/seats
        -> { showId, seats: [{seatId,row,col,type,status:FREE|HELD|BOOKED}], holdTtlSec }
   POST /shows/{showId}/hold
        { userId, seatIds:[...], ttlSec }
        -> { holdId, expiresAt }
   POST /bookings
        { holdId, userId }
        -> { bookingId, amount, seats:[...], qr }
   POST /payments/confirm
        { bookingId, method, txnRef? }
        -> { paymentId, status }

4) define services involved
   ShowSearchService     - list shows for movie/city/date.
   SeatInventoryService  - seat map, create hold (per-show lock), check expiries.
   BookingService        - confirm booking from hold (per-show lock), pricing.
   PaymentService        - stub payment confirmation.
   IdGenerator           - simple IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   movie(id PK, title, duration_min)
   theater(id PK, city, name)
   screen(id PK, theater_id FK, name, rows, cols)
   seat(id PK, screen_id FK, row, col, type ENUM)
   show(id PK, movie_id FK, screen_id FK, start_at, base_price NUM, status)
   seat_hold(id PK, show_id FK, user_id, seat_ids JSON, expires_at, active)
      INDEX(show_id, active, expires_at)
   booking(id PK, show_id FK, user_id, seat_ids JSON, amount NUM, status, qr)
      INDEX(show_id, status)
   payment(id PK, booking_id FK UNIQUE, method, amount NUM, status, txn_ref, paid_at)
*/

import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/* ===== Enums ===== */
enum SeatType { REGULAR, PREMIUM }
enum BookingStatus { PENDING, CONFIRMED, CANCELLED }
enum PaymentStatus { PENDING, PAID, FAILED }

/* ===== Domain ===== */
final class Movie { final String id, title; final int durationMin; Movie(String id,String title,int d){this.id=id;this.title=title;this.durationMin=d;} }
final class Theater { final String id, city, name; Theater(String id,String city,String name){this.id=id;this.city=city;this.name=name;} }
final class Screen { final String id, theaterId, name; final int rows, cols; Screen(String id,String th,String name,int r,int c){this.id=id;this.theaterId=th;this.name=name;this.rows=r;this.cols=c;} }
final class Seat { final String id, screenId; final int row, col; final SeatType type; Seat(String id,String sid,int r,int c,SeatType t){this.id=id;this.screenId=sid;this.row=r;this.col=c;this.type=t;} }
final class Show { final String id, movieId, screenId; final ZonedDateTime startAt; final double basePrice; Show(String id,String mid,String sc,ZonedDateTime t,double p){this.id=id;this.movieId=mid;this.screenId=sc;this.startAt=t;this.basePrice=p;} }

final class SeatHold {
    final String id, showId, userId; final Set<String> seatIds;
    final Instant expiresAt; volatile boolean active=true;
    SeatHold(String id,String showId,String userId,Set<String> seatIds,Instant exp){this.id=id;this.showId=showId;this.userId=userId;this.seatIds=seatIds;this.expiresAt=exp;}
}

final class Booking {
    final String id, showId, userId, qr;
    final Set<String> seatIds;
    final double amount; volatile BookingStatus status=BookingStatus.CONFIRMED;
    Booking(String id,String showId,String userId,Set<String> seatIds,double amount,String qr){
        this.id=id;this.showId=showId;this.userId=userId;this.seatIds=seatIds;this.amount=amount;this.qr=qr;
    }
}

final class Payment {
    final String id, bookingId, method, txnRef; final double amount;
    volatile PaymentStatus status=PaymentStatus.PENDING; volatile Instant paidAt;
    Payment(String id,String b,String m,String x,double a){this.id=id;this.bookingId=b;this.method=m;this.txnRef=x;this.amount=a;}
}

/* ===== Repos (in-memory) ===== */
class Ids { private final AtomicLong n=new AtomicLong(1); String next(String p){ return p+"-"+n.getAndIncrement(); } }

class MoviesRepo { final Map<String,Movie> m=new ConcurrentHashMap<>(); Movie save(Movie x){m.put(x.id,x);return x;} Optional<Movie> byId(String id){return Optional.ofNullable(m.get(id));} }
class TheatersRepo { final Map<String,Theater> m=new ConcurrentHashMap<>(); Theater save(Theater x){m.put(x.id,x);return x;} Optional<Theater> byId(String id){return Optional.ofNullable(m.get(id));} }
class ScreensRepo { final Map<String,Screen> m=new ConcurrentHashMap<>(); Screen save(Screen x){m.put(x.id,x);return x;} Optional<Screen> byId(String id){return Optional.ofNullable(m.get(id));} }
class SeatsRepo {
    final Map<String,Seat> m=new ConcurrentHashMap<>();
    Seat save(Seat s){m.put(s.id,s);return s;}
    List<Seat> byScreen(String screenId){ return m.values().stream().filter(s->s.screenId.equals(screenId)).collect(Collectors.toList()); }
    Optional<Seat> byId(String id){return Optional.ofNullable(m.get(id));}
}
class ShowsRepo { final Map<String,Show> m=new ConcurrentHashMap<>(); Show save(Show x){m.put(x.id,x);return x;} Optional<Show> byId(String id){return Optional.ofNullable(m.get(id));} List<Show> all(){return new ArrayList<>(m.values());} }
class HoldsRepo {
    final Map<String,SeatHold> m=new ConcurrentHashMap<>();
    SeatHold save(SeatHold h){m.put(h.id,h);return h;}
    Optional<SeatHold> byId(String id){return Optional.ofNullable(m.get(id));}
    List<SeatHold> activeByShow(String showId){
        Instant now=Instant.now();
        return m.values().stream().filter(h->h.showId.equals(showId)&&h.active&&h.expiresAt.isAfter(now)).collect(Collectors.toList());
    }
}
class BookingsRepo {
    final Map<String,Booking> m=new ConcurrentHashMap<>();
    Booking save(Booking b){m.put(b.id,b);return b;}
    List<Booking> byShow(String showId){ return m.values().stream().filter(b->b.showId.equals(showId)&&b.status==BookingStatus.CONFIRMED).collect(Collectors.toList()); }
}
class PaymentsRepo {
    final Map<String,Payment> m=new ConcurrentHashMap<>();
    Payment save(Payment p){m.put(p.id,p);return p;}
    Optional<Payment> byBooking(String bookingId){ return m.values().stream().filter(p->p.bookingId.equals(bookingId)).findFirst(); }
}

/* ===== Errors ===== */
class DomainException extends RuntimeException { DomainException(String m){super(m);} }

/* ===== Services ===== */
class ShowSearchService {
    private final ShowsRepo shows; private final TheatersRepo theaters;
    ShowSearchService(ShowsRepo s, TheatersRepo t){shows=s;theaters=t;}
    List<Show> list(String movieId, String city, LocalDate date){
        return shows.all().stream()
                .filter(sh->sh.movieId.equals(movieId))
                .filter(sh->theaters.byId(sh.screenId.split(":")[0]).map(th->th.city.equalsIgnoreCase(city)).orElse(true))
                .filter(sh->sh.startAt.toLocalDate().equals(date))
                .collect(Collectors.toList());
    }
}

class PerShowLocks {
    private final ConcurrentHashMap<String, ReentrantLock> locks = new ConcurrentHashMap<>();
    ReentrantLock lockFor(String showId){ return locks.computeIfAbsent(showId, k->new ReentrantLock(true)); }
}

class SeatInventoryService {
    private final ShowsRepo shows; private final ScreensRepo screens; private final SeatsRepo seats;
    private final HoldsRepo holds; private final BookingsRepo bookings; private final PerShowLocks locks;

    SeatInventoryService(ShowsRepo sh,ScreensRepo sc,SeatsRepo se,HoldsRepo h,BookingsRepo b,PerShowLocks L){
        shows=sh; screens=sc; seats=se; holds=h; bookings=b; locks=L;
    }

    static final class SeatView {
        final String seatId; final int row, col; final SeatType type; final String status;
        SeatView(String id,int r,int c,SeatType t,String s){seatId=id;row=r;col=c;type=t;status=s;}
        public String toString(){ return seatId+":"+status; }
    }

    List<SeatView> seatMap(String showId){
        Show show = shows.byId(showId).orElseThrow(()->new DomainException("show not found"));
        Screen screen = screens.byId(show.screenId).orElseThrow(()->new DomainException("screen not found"));
        List<Seat> allSeats = seats.byScreen(screen.id);
        Set<String> booked = bookings.byShow(showId).stream().flatMap(b->b.seatIds.stream()).collect(Collectors.toSet());
        Set<String> held = holds.activeByShow(showId).stream().flatMap(h->h.seatIds.stream()).collect(Collectors.toSet());
        List<SeatView> out = new ArrayList<>();
        for (Seat s: allSeats){
            String status = booked.contains(s.id) ? "BOOKED" : (held.contains(s.id) ? "HELD" : "FREE");
            out.add(new SeatView(s.id, s.row, s.col, s.type, status));
        }
        out.sort(Comparator.comparingInt((SeatView v)->v.row).thenComparingInt(v->v.col));
        return out;
    }

    SeatHold holdSeats(String showId, String userId, Set<String> seatIds, Duration ttl){
        ReentrantLock lock = locks.lockFor(showId);
        lock.lock();
        try{
            // filter out expired automatically (holds.activeByShow uses time)
            Set<String> booked = bookings.byShow(showId).stream().flatMap(b->b.seatIds.stream()).collect(Collectors.toSet());
            Set<String> held = holds.activeByShow(showId).stream().flatMap(h->h.seatIds.stream()).collect(Collectors.toSet());

            // validate requested seats exist & are free
            for (String seatId: seatIds){
                if (booked.contains(seatId) || held.contains(seatId)) throw new DomainException("seat not available: "+seatId);
            }
            SeatHold h = new SeatHold(BookMyShow40Min.ids.next("hold"), showId, userId, seatIds, Instant.now().plus(ttl));
            return holds.save(h);
        } finally { lock.unlock(); }
    }
}

class BookingService {
    private final ShowsRepo shows; private final HoldsRepo holds; private final BookingsRepo bookings; private final PaymentsRepo payments; private final PerShowLocks locks;

    BookingService(ShowsRepo sh,HoldsRepo h,BookingsRepo b,PaymentsRepo p,PerShowLocks L){
        shows=sh; holds=h; bookings=b; payments=p; locks=L;
    }

    Booking confirm(String holdId){
        SeatHold h = holds.byId(holdId).orElseThrow(()->new DomainException("hold not found"));
        if (!h.active || h.expiresAt.isBefore(Instant.now())) throw new DomainException("hold expired");
        ReentrantLock lock = locks.lockFor(h.showId);
        lock.lock();
        try{
            // re-check availability under lock
            // (if any seat is already booked meanwhile, fail)
            // Collect currently booked seats for the show:
            Set<String> booked = bookings.byShow(h.showId).stream().flatMap(b->b.seatIds.stream()).collect(Collectors.toSet());
            for (String s: h.seatIds) if (booked.contains(s)) throw new DomainException("seat got booked: "+s);

            Show show = shows.byId(h.showId).orElseThrow(()->new DomainException("show not found"));
            double price = show.basePrice * h.seatIds.size();
            String qr = UUID.randomUUID().toString();
            Booking b = new Booking(BookMyShow40Min.ids.next("bkg"), h.showId, h.userId, new HashSet<>(h.seatIds), round2(price), qr);
            h.active = false; // consume hold
            return bookings.save(b);
        } finally { lock.unlock(); }
    }

    private static double round2(double v){ return Math.round(v*100.0)/100.0; }
}

class PaymentService {
    private final PaymentsRepo payments;
    PaymentService(PaymentsRepo p){payments=p;}
    Payment confirm(String bookingId, double amount, String method, String txnRef){
        Payment pay = new Payment(BookMyShow40Min.ids.next("pay"), bookingId, method, txnRef, amount);
        pay.status = PaymentStatus.PAID; pay.paidAt = Instant.now(); // simulate success
        return payments.save(pay);
    }
}

/* ===== Controller Facade (mirrors the APIs) ===== */
class BookingController {
    private final ShowSearchService search; private final SeatInventoryService inv; private final BookingService bookings; private final PaymentService payments;

    BookingController(ShowSearchService s, SeatInventoryService i, BookingService b, PaymentService p){
        search=s; inv=i; bookings=b; payments=p;
    }

    List<Show> getShows(String movieId, String city, LocalDate date){ return search.list(movieId, city, date); }

    List<SeatInventoryService.SeatView> getSeatMap(String showId){ return inv.seatMap(showId); }

    SeatHold postHold(String showId, String userId, Set<String> seatIds, long ttlSec){
        return inv.holdSeats(showId, userId, seatIds, Duration.ofSeconds(ttlSec));
    }

    Booking postBooking(String holdId){ return bookings.confirm(holdId); }

    Payment postPayment(String bookingId, double amount, String method, String txnRef){
        return payments.confirm(bookingId, amount, method, txnRef);
    }
}

/* ===== Bootstrap & Demo (tiny, 40-min compatible) ===== */
public class BookMyShow40Min {
    static final Ids ids = new Ids();

    public static void main(String[] args) {
        // Repos
        MoviesRepo movies = new MoviesRepo();
        TheatersRepo theaters = new TheatersRepo();
        ScreensRepo screens = new ScreensRepo();
        SeatsRepo seats = new SeatsRepo();
        ShowsRepo shows = new ShowsRepo();
        HoldsRepo holds = new HoldsRepo();
        BookingsRepo bookings = new BookingsRepo();
        PaymentsRepo payments = new PaymentsRepo();

        // Seed
        Movie m = movies.save(new Movie(ids.next("mov"), "Interstellar", 169));
        Theater th = theaters.save(new Theater("TH-1:SCR-1", "Bengaluru", "Galaxy Cinema"));
        Screen sc = screens.save(new Screen("SCR-1", th.id, "Screen 1", 3, 4)); // small 3x4 for demo
        // Seats
        for (int r=1;r<=sc.rows;r++){
            for (int c=1;c<=sc.cols;c++){
                SeatType type = (r==1?SeatType.PREMIUM:SeatType.REGULAR);
                seats.save(new Seat("SEAT-"+r+"-"+c, sc.id, r, c, type));
            }
        }
        // Show (note: we embed theater id in Show.screenId owner link for city mapping shortcut)
        ZonedDateTime start = ZonedDateTime.of(LocalDate.now(), LocalTime.of(19,0), ZoneId.of("Asia/Kolkata"));
        Show sh = shows.save(new Show(ids.next("show"), m.id, sc.id, start, 250.0));

        // Services
        PerShowLocks locks = new PerShowLocks();
        ShowSearchService search = new ShowSearchService(shows, theaters);
        SeatInventoryService inventory = new SeatInventoryService(shows, screens, seats, holds, bookings, locks);
        BookingService bookingSvc = new BookingService(shows, holds, bookings, payments, locks);
        PaymentService paymentSvc = new PaymentService(payments);

        // Controller
        BookingController api = new BookingController(search, inventory, bookingSvc, paymentSvc);

        // --- Demo flow (as API calls) ---
        System.out.println("GET /movies/{movieId}/shows?city=Bengaluru&date=today");
        System.out.println(api.getShows(m.id, "Bengaluru", LocalDate.now()));

        System.out.println("\nGET /shows/{showId}/seats");
        System.out.println(api.getSeatMap(sh.id));

        System.out.println("\nPOST /shows/{showId}/hold  seats=[SEAT-1-1, SEAT-1-2]");
        SeatHold hold = api.postHold(sh.id, "user-42", setOf("SEAT-1-1","SEAT-1-2"), 300);
        System.out.println("Hold: "+hold.id+" expiresAt="+hold.expiresAt);

        System.out.println("\nGET /shows/{showId}/seats  (after hold)");
        System.out.println(api.getSeatMap(sh.id));

        System.out.println("\nPOST /bookings  {holdId}");
        Booking booking = api.postBooking(hold.id);
        System.out.println("Booking: "+booking.id+" seats="+booking.seatIds+" amount="+booking.amount+" qr="+booking.qr);

        System.out.println("\nPOST /payments/confirm");
        Payment pay = api.postPayment(booking.id, booking.amount, "UPI", "TXN-123");
        System.out.println("Payment: "+pay.id+" status="+pay.status+" paidAt="+pay.paidAt);

        System.out.println("\nGET /shows/{showId}/seats  (after booking)");
        System.out.println(api.getSeatMap(sh.id));
    }

    private static Set<String> setOf(String...xs){ return new HashSet<>(Arrays.asList(xs)); }
}
```

## Food Delivery

```
/*
Template ->
1) define functional requirements
   - Browse restaurants by area/cuisine; view menu items (veg/non-veg).
   - Create cart per user per restaurant; add/remove items; compute totals, taxes, delivery fee.
   - Place order (from a single restaurant), capture address & instructions.
   - Payment confirmation (stub) → move order to PLACED/PAID.
   - Assign nearest available delivery partner; update order status (PREPARING → PICKED_UP → DELIVERED).
   - Track order with ETA; list user's past orders.
   - In-memory implementation; single city; thread-safe where needed; deliverable in ~40 min.

2) define entities / actors
   Actors: Customer, Restaurant, DeliveryPartner, System/PaymentGateway (stub)
   Entities: Restaurant, MenuItem, Cart, CartItem, Order, OrderItem, Payment, DeliveryPartner, GeoPoint

3) define apis - get/post/put, request, response  (mirrored by controller methods)
   GET  /restaurants?area=HSR&cuisine=NorthIndian     -> [restaurant...]
   GET  /restaurants/{id}/menu                        -> [menuItem...]
   POST /cart/items                                   {userId, restaurantId, itemId, qty} -> cart view
   DELETE /cart/items                                 {userId, itemId} -> cart view
   POST /orders                                       {userId, address, instructions?} -> {orderId, amount}
   POST /payments/confirm                             {orderId, method, txnRef?} -> {paymentId, status}
   POST /orders/{orderId}/assign                      -> {partnerId, etaMin}
   GET  /orders/{orderId}/track                       -> {status, etaMin, partnerLoc?}

4) define services involved
   CatalogService        - search restaurants, menu retrieval
   CartService           - add/remove, compute totals
   PricingService        - taxes (e.g., 5%), delivery fee (distance slab), surge hooks
   OrderService          - place & manage order lifecycle
   PaymentService        - confirm payments (stub)
   AssignmentService     - choose nearest available delivery partner
   TrackingService       - ETA calc & status updates
   IdGenerator           - ID generation

5) define db schema - what all tables are required, what are the columns, what are the keys
   restaurant(id PK, name, area, cuisines JSON, lat, lon, rating)
   menu_item(id PK, restaurant_id FK, name, price, veg BOOL, in_stock BOOL)
   cart(id PK, user_id, restaurant_id, updated_at)
   cart_item(id PK, cart_id FK, item_id FK, qty)
   order(id PK, user_id, restaurant_id, address, instructions, status, sub_total, tax, delivery_fee, total, created_at)
   order_item(id PK, order_id FK, item_id FK, name_snapshot, price_snapshot, qty)
   payment(id PK, order_id FK UNIQUE, method, amount, txn_ref, status, paid_at)
   delivery_partner(id PK, name, lat, lon, available BOOL, rating)
*/
```

### Java Implementation

```java
/*
Template ->
1) define functional requirements
   - Browse restaurants by area/cuisine; view menu items (veg/non-veg).
   - Create cart per user per restaurant; add/remove items; compute totals, taxes, delivery fee.
   - Place order (from a single restaurant), capture address & instructions.
   - Payment confirmation (stub) → move order to PLACED/PAID.
   - Assign nearest available delivery partner; update order status (PREPARING → PICKED_UP → DELIVERED).
   - Track order with ETA; list user's past orders.
   - In-memory implementation; single city; thread-safe where needed; deliverable in ~40 min.

2) define entities / actors
   Actors: Customer, Restaurant, DeliveryPartner, System/PaymentGateway (stub)
   Entities: Restaurant, MenuItem, Cart, CartItem, Order, OrderItem, Payment, DeliveryPartner, GeoPoint

3) define apis - get/post/put, request, response  (mirrored by controller methods)
   GET  /restaurants?area=HSR&cuisine=NorthIndian     -> [restaurant...]
   GET  /restaurants/{id}/menu                        -> [menuItem...]
   POST /cart/items                                   {userId, restaurantId, itemId, qty} -> cart view
   DELETE /cart/items                                 {userId, itemId} -> cart view
   POST /orders                                       {userId, address, instructions?} -> {orderId, amount}
   POST /payments/confirm                             {orderId, method, txnRef?} -> {paymentId, status}
   POST /orders/{orderId}/assign                      -> {partnerId, etaMin}
   GET  /orders/{orderId}/track                       -> {status, etaMin, partnerLoc?}

4) define services involved
   CatalogService        - search restaurants, menu retrieval
   CartService           - add/remove, compute totals
   PricingService        - taxes (e.g., 5%), delivery fee (distance slab), surge hooks
   OrderService          - place & manage order lifecycle
   PaymentService        - confirm payments (stub)
   AssignmentService     - choose nearest available delivery partner
   TrackingService       - ETA calc & status updates
   IdGenerator           - ID generation

5) define db schema - what all tables are required, what are the columns, what are the keys
   restaurant(id PK, name, area, cuisines JSON, lat, lon, rating)
   menu_item(id PK, restaurant_id FK, name, price, veg BOOL, in_stock BOOL)
   cart(id PK, user_id, restaurant_id, updated_at)
   cart_item(id PK, cart_id FK, item_id FK, qty)
   order(id PK, user_id, restaurant_id, address, instructions, status, sub_total, tax, delivery_fee, total, created_at)
   order_item(id PK, order_id FK, item_id FK, name_snapshot, price_snapshot, qty)
   payment(id PK, order_id FK UNIQUE, method, amount, txn_ref, status, paid_at)
   delivery_partner(id PK, name, lat, lon, available BOOL, rating)
*/

import java.time.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/* ===== Domain ===== */
enum OrderStatus { CART, PLACED, PAID, PREPARING, PICKED_UP, DELIVERED, CANCELLED }
enum PaymentStatus { PENDING, PAID, FAILED }

final class GeoPoint { final double lat, lon; GeoPoint(double lat,double lon){this.lat=lat;this.lon=lon;} }
final class Restaurant {
    final String id, name, area; final List<String> cuisines; final GeoPoint loc; final double rating;
    Restaurant(String id,String name,String area,List<String> cuisines,GeoPoint loc,double rating){
        this.id=id; this.name=name; this.area=area; this.cuisines=cuisines; this.loc=loc; this.rating=rating;
    }
}
final class MenuItem {
    final String id, restaurantId, name; final double price; final boolean veg; volatile boolean inStock;
    MenuItem(String id,String rid,String name,double price,boolean veg,boolean inStock){
        this.id=id; this.restaurantId=rid; this.name=name; this.price=price; this.veg=veg; this.inStock=inStock;
    }
}

final class CartItem { final String itemId; int qty; CartItem(String itemId,int qty){this.itemId=itemId; this.qty=qty;} }
final class Cart {
    final String id, userId, restaurantId; final Map<String,CartItem> items = new LinkedHashMap<>();
    volatile Instant updatedAt = Instant.now();
    Cart(String id,String userId,String restaurantId){this.id=id; this.userId=userId; this.restaurantId=restaurantId;}
}

final class OrderItem {
    final String itemId, nameSnapshot; final double priceSnapshot; final int qty;
    OrderItem(String itemId,String name,double price,int qty){this.itemId=itemId;this.nameSnapshot=name;this.priceSnapshot=price;this.qty=qty;}
}
final class Order {
    final String id, userId, restaurantId, address, instructions;
    final List<OrderItem> items;
    volatile OrderStatus status = OrderStatus.PLACED;
    final double subTotal, tax, deliveryFee, total;
    volatile Instant createdAt = Instant.now();
    volatile String partnerId; volatile Integer etaMin;
    Order(String id,String userId,String restaurantId,String address,String instr,List<OrderItem> items,
          double sub,double tax,double del,double tot){
        this.id=id;this.userId=userId;this.restaurantId=restaurantId;this.address=address;this.instructions=instr;this.items=items;
        this.subTotal=sub; this.tax=tax; this.deliveryFee=del; this.total=tot;
    }
}

final class Payment {
    final String id, orderId, method, txnRef; final double amount;
    volatile PaymentStatus status = PaymentStatus.PENDING; volatile Instant paidAt;
    Payment(String id,String orderId,String method,String txnRef,double amount){
        this.id=id; this.orderId=orderId; this.method=method; this.txnRef=txnRef; this.amount=amount;
    }
}

final class DeliveryPartner {
    final String id, name; volatile GeoPoint loc; volatile boolean available; final double rating;
    DeliveryPartner(String id,String name,GeoPoint loc,boolean available,double rating){
        this.id=id; this.name=name; this.loc=loc; this.available=available; this.rating=rating;
    }
}

/* ===== Repos (in-memory) ===== */
class Ids { private final AtomicLong n=new AtomicLong(1); String next(String p){return p+"-"+n.getAndIncrement();} }

class RestaurantRepo {
    final Map<String,Restaurant> m=new ConcurrentHashMap<>();
    Restaurant save(Restaurant r){m.put(r.id,r);return r;}
    List<Restaurant> search(String area,String cuisine){
        return m.values().stream()
                .filter(r->area==null||r.area.equalsIgnoreCase(area))
                .filter(r->cuisine==null||r.cuisines.stream().anyMatch(c->c.equalsIgnoreCase(cuisine)))
                .sorted(Comparator.comparingDouble((Restaurant r)->-r.rating))
                .collect(Collectors.toList());
    }
    Optional<Restaurant> byId(String id){ return Optional.ofNullable(m.get(id)); }
}
class MenuRepo {
    final Map<String,MenuItem> m=new ConcurrentHashMap<>();
    MenuItem save(MenuItem x){m.put(x.id,x);return x;}
    List<MenuItem> byRestaurant(String rid){ return m.values().stream().filter(i->i.restaurantId.equals(rid)).collect(Collectors.toList()); }
    Optional<MenuItem> byId(String id){ return Optional.ofNullable(m.get(id)); }
}
class CartRepo {
    final Map<String,Cart> m=new ConcurrentHashMap<>(); // key: userId
    Cart save(Cart c){ m.put(c.userId, c); return c; }
    Optional<Cart> byUser(String userId){ return Optional.ofNullable(m.get(userId)); }
    void delete(String userId){ m.remove(userId); }
}
class OrderRepo {
    final Map<String,Order> m=new ConcurrentHashMap<>();
    Order save(Order o){ m.put(o.id,o); return o; }
    Optional<Order> byId(String id){ return Optional.ofNullable(m.get(id)); }
    List<Order> byUser(String user){ return m.values().stream().filter(o->o.userId.equals(user)).collect(Collectors.toList()); }
}
class PaymentRepo {
    final Map<String,Payment> m=new ConcurrentHashMap<>();
    Payment save(Payment p){ m.put(p.id,p); return p; }
    Optional<Payment> byOrder(String orderId){ return m.values().stream().filter(x->x.orderId.equals(orderId)).findFirst(); }
}
class PartnerRepo {
    final Map<String,DeliveryPartner> m=new ConcurrentHashMap<>();
    DeliveryPartner save(DeliveryPartner p){ m.put(p.id,p); return p; }
    List<DeliveryPartner> available(){ return m.values().stream().filter(p->p.available).collect(Collectors.toList()); }
    Optional<DeliveryPartner> byId(String id){ return Optional.ofNullable(m.get(id)); }
}

/* ===== Utils ===== */
class Haversine {
    static double distanceKm(GeoPoint a, GeoPoint b){
        double R=6371.0, dLat=Math.toRadians(b.lat-a.lat), dLon=Math.toRadians(b.lon-a.lon);
        double s1=Math.sin(dLat/2), s2=Math.sin(dLon/2);
        double aa=s1*s1 + Math.cos(Math.toRadians(a.lat))*Math.cos(Math.toRadians(b.lat))*s2*s2;
        return 2*R*Math.asin(Math.sqrt(aa));
    }
    static int etaMin(double km){ return Math.max(6, (int)Math.round(km/0.35)); } // ~21 km/h avg
}
class DomainException extends RuntimeException { DomainException(String m){super(m);} }

/* ===== Services ===== */
class CatalogService {
    private final RestaurantRepo restaurants; private final MenuRepo menu;
    CatalogService(RestaurantRepo r, MenuRepo m){restaurants=r; menu=m;}
    List<Restaurant> search(String area,String cuisine){ return restaurants.search(area, cuisine); }
    List<MenuItem> menu(String restaurantId){ return menu.byRestaurant(restaurantId); }
}
class PricingService {
    private final double taxRate = 0.05; // 5%
    double subTotal(List<OrderItem> items){ return round2(items.stream().mapToDouble(i->i.priceSnapshot*i.qty).sum()); }
    double tax(double sub){ return round2(sub * taxRate); }
    double deliveryFee(double distanceKm){
        double fee = distanceKm<=2 ? 20 : (distanceKm<=5 ? 35 : 50 + (distanceKm-5)*5);
        return round2(fee);
    }
    double total(double sub,double tax,double del){ return round2(sub+tax+del); }
    static double round2(double v){ return Math.round(v*100.0)/100.0; }
}
class CartService {
    private final CartRepo carts; private final MenuRepo menu; private final Ids ids;
    CartService(CartRepo c, MenuRepo m, Ids ids){carts=c;menu=m;this.ids=ids;}
    synchronized Cart addItem(String userId, String restaurantId, String itemId, int qty){
        MenuItem mi = menu.byId(itemId).orElseThrow(()->new DomainException("item not found"));
        if (!mi.inStock) throw new DomainException("item out of stock");
        Cart cart = carts.byUser(userId).orElse(null);
        if (cart==null) cart = carts.save(new Cart(ids.next("cart"), userId, restaurantId));
        if (!cart.restaurantId.equals(restaurantId)) throw new DomainException("cart restricted to 1 restaurant");
        CartItem ci = cart.items.getOrDefault(itemId, new CartItem(itemId,0));
        ci.qty += qty;
        if (ci.qty<=0) cart.items.remove(itemId); else cart.items.put(itemId, ci);
        cart.updatedAt = Instant.now();
        return carts.save(cart);
    }
    synchronized Cart removeItem(String userId, String itemId){
        Cart cart = carts.byUser(userId).orElseThrow(()->new DomainException("cart not found"));
        cart.items.remove(itemId);
        cart.updatedAt = Instant.now();
        return carts.save(cart);
    }
    synchronized void clear(String userId){ carts.delete(userId); }
}
class OrderService {
    private final OrderRepo orders; private final CartRepo carts; private final MenuRepo menu; private final PricingService pricing; private final RestaurantRepo restaurants; private final Ids ids;
    OrderService(OrderRepo o, CartRepo c, MenuRepo m, PricingService p, RestaurantRepo r, Ids ids){
        orders=o;carts=c;menu=m;pricing=p;restaurants=r;this.ids=ids;
    }
    synchronized Order place(String userId, String address, String instructions){
        Cart cart = carts.byUser(userId).orElseThrow(()->new DomainException("empty cart"));
        if (cart.items.isEmpty()) throw new DomainException("empty cart");
        Restaurant rest = restaurants.byId(cart.restaurantId).orElseThrow(()->new DomainException("restaurant"));
        // snapshot items
        List<OrderItem> items = new ArrayList<>();
        for (CartItem ci: cart.items.values()){
            MenuItem mi = menu.byId(ci.itemId).orElseThrow(()->new DomainException("menu item missing"));
            if (!mi.inStock) throw new DomainException("item went out of stock: "+mi.name);
            items.add(new OrderItem(mi.id, mi.name, mi.price, ci.qty));
        }
        double sub = pricing.subTotal(items);
        // distance approx: pretend user's address is 2km away baseline (for demo).
        double distKm = 2.0; // could be from geocode(address)
        double delivery = pricing.deliveryFee(distKm);
        double tax = pricing.tax(sub);
        double total = pricing.total(sub, tax, delivery);
        Order order = new Order(ids.next("ord"), userId, rest.id, address, instructions, items, sub, tax, delivery, total);
        carts.delete(userId); // clear cart
        return orders.save(order);
    }
    void setStatus(String orderId, OrderStatus st){
        Order o = orders.byId(orderId).orElseThrow(()->new DomainException("order"));
        o.status = st; orders.save(o);
    }
}
class PaymentService {
    private final PaymentRepo payments; private final OrderRepo orders; private final Ids ids;
    PaymentService(PaymentRepo p, OrderRepo o, Ids ids){payments=p;orders=o;this.ids=ids;}
    synchronized Payment confirm(String orderId, String method, String txnRef){
        Order o = orders.byId(orderId).orElseThrow(()->new DomainException("order"));
        Payment pay = new Payment(ids.next("pay"), orderId, method, txnRef, o.total);
        pay.status = PaymentStatus.PAID; pay.paidAt = Instant.now();
        orders.save(o); // status handled externally
        return payments.save(pay);
    }
}
class AssignmentService {
    private final PartnerRepo partners; private final RestaurantRepo restaurants; private final OrderRepo orders;
    AssignmentService(PartnerRepo p, RestaurantRepo r, OrderRepo o){partners=p;restaurants=r;orders=o;}
    synchronized DeliveryPartner assign(String orderId){
        Order o = orders.byId(orderId).orElseThrow(()->new DomainException("order"));
        Restaurant r = restaurants.byId(o.restaurantId).orElseThrow(()->new DomainException("restaurant"));
        List<DeliveryPartner> avail = partners.available();
        if (avail.isEmpty()) throw new DomainException("no partner available");
        // nearest partner by distance to restaurant
        DeliveryPartner best = avail.stream()
                .min(Comparator.comparingDouble(p->Haversine.distanceKm(p.loc, r.loc))).get();
        best.available = false;
        double km = Haversine.distanceKm(best.loc, r.loc);
        int eta = Haversine.etaMin(km + 2.0); // add 2km headroom to destination
        o.partnerId = best.id; o.etaMin = eta; orders.save(o);
        return best;
    }
    synchronized void markDelivered(String orderId){
        Order o = orders.byId(orderId).orElseThrow(()->new DomainException("order"));
        if (o.partnerId!=null){
            partners.byId(o.partnerId).ifPresent(p->p.available=true);
        }
        o.status = OrderStatus.DELIVERED; orders.save(o);
    }
}
class TrackingService {
    private final OrderRepo orders; private final PartnerRepo partners; private final RestaurantRepo restaurants;
    TrackingService(OrderRepo o, PartnerRepo p, RestaurantRepo r){orders=o;partners=p;restaurants=r;}
    Map<String,Object> track(String orderId){
        Order o = orders.byId(orderId).orElseThrow(()->new DomainException("order"));
        Map<String,Object> m = new LinkedHashMap<>();
        m.put("status", o.status.name());
        m.put("etaMin", o.etaMin);
        if (o.partnerId!=null) {
            partners.byId(o.partnerId).ifPresent(dp->{
                m.put("partnerId", dp.id);
                m.put("partnerLoc", Map.of("lat", dp.loc.lat, "lon", dp.loc.lon));
            });
        }
        return m;
    }
}

/* ===== Controller Facade ===== */
class FoodController {
    private final CatalogService catalog; private final CartService carts; private final OrderService orders;
    private final PaymentService payments; private final AssignmentService assign; private final TrackingService tracking;

    FoodController(CatalogService c, CartService ca, OrderService o, PaymentService p, AssignmentService a, TrackingService t){
        catalog=c; carts=ca; orders=o; payments=p; assign=a; tracking=t;
    }

    List<Restaurant> getRestaurants(String area,String cuisine){ return catalog.search(area, cuisine); }
    List<MenuItem> getMenu(String restaurantId){ return catalog.menu(restaurantId); }

    Cart postCartAdd(String userId, String restaurantId, String itemId, int qty){ return carts.addItem(userId, restaurantId, itemId, qty); }
    Cart deleteCartItem(String userId, String itemId){ return carts.removeItem(userId, itemId); }

    Order postOrder(String userId, String address, String instructions){ return orders.place(userId, address, instructions); }
    Payment postPaymentConfirm(String orderId, String method, String txnRef){ return payments.confirm(orderId, method, txnRef); }

    DeliveryPartner postAssign(String orderId){
        DeliveryPartner dp = assign.assign(orderId);
        orders.setStatus(orderId, OrderStatus.PREPARING);
        return dp;
    }
    Map<String,Object> getTrack(String orderId){ return tracking.track(orderId); }
}

/* ===== Bootstrap & Minimal Demo ===== */
public class SwiggyZomato40Min {
    public static void main(String[] args) {
        Ids ids = new Ids();
        // Repos
        RestaurantRepo restaurants = new RestaurantRepo();
        MenuRepo menu = new MenuRepo();
        CartRepo carts = new CartRepo();
        OrderRepo orders = new OrderRepo();
        PaymentRepo pays = new PaymentRepo();
        PartnerRepo partners = new PartnerRepo();

        // Seed Restaurants & Menu
        Restaurant r1 = restaurants.save(new Restaurant(ids.next("rest"), "Punjabi Zaika", "HSR", List.of("NorthIndian","Biryani"), new GeoPoint(12.91,77.64), 4.4));
        Restaurant r2 = restaurants.save(new Restaurant(ids.next("rest"), "Veggie Delite", "HSR", List.of("SouthIndian","Healthy"), new GeoPoint(12.905,77.64), 4.6));

        menu.save(new MenuItem(ids.next("item"), r1.id, "Butter Chicken", 280, false, true));
        menu.save(new MenuItem(ids.next("item"), r1.id, "Dal Makhani", 180, true, true));
        menu.save(new MenuItem(ids.next("item"), r2.id, "Veg Thali", 220, true, true));

        // Partners
        partners.save(new DeliveryPartner(ids.next("dp"), "Ravi", new GeoPoint(12.90,77.62), true, 4.8));
        partners.save(new DeliveryPartner(ids.next("dp"), "Kiran", new GeoPoint(12.92,77.65), true, 4.5));

        // Services
        CatalogService catalog = new CatalogService(restaurants, menu);
        PricingService pricing = new PricingService();
        CartService cartSvc = new CartService(carts, menu, ids);
        OrderService orderSvc = new OrderService(orders, carts, menu, pricing, restaurants, ids);
        PaymentService paymentSvc = new PaymentService(pays, orders, ids);
        AssignmentService assign = new AssignmentService(partners, restaurants, orders);
        TrackingService tracking = new TrackingService(orders, partners, restaurants);

        // Controller
        FoodController api = new FoodController(catalog, cartSvc, orderSvc, paymentSvc, assign, tracking);

        // --- Demo like API calls ---
        System.out.println("GET /restaurants?area=HSR&cuisine=NorthIndian\n" + api.getRestaurants("HSR","NorthIndian"));
        System.out.println("\nGET /restaurants/{id}/menu\n" + api.getMenu(r1.id));

        String user = "user-007";
        var c1 = api.postCartAdd(user, r1.id, api.getMenu(r1.id).get(0).id, 1);
        var c2 = api.postCartAdd(user, r1.id, api.getMenu(r1.id).get(1).id, 2);
        System.out.println("\nPOST /cart/items -> cart items: " + c2.items.values().stream().map(ci->ci.itemId+":"+ci.qty).collect(Collectors.toList()));

        Order ord = api.postOrder(user, "HSR Layout, Bengaluru", "Less spicy");
        System.out.println("\nPOST /orders -> " + ord.id + " total=" + ord.total);

        var pay = api.postPaymentConfirm(ord.id, "UPI", "TXN-42");
        orders.byId(ord.id).ifPresent(o->o.status=OrderStatus.PAID);
        System.out.println("POST /payments/confirm -> " + pay.status + " amount=" + pay.amount);

        DeliveryPartner dp = api.postAssign(ord.id);
        System.out.println("\nPOST /orders/{id}/assign -> partner=" + dp.name + " etaMin=" + orders.byId(ord.id).get().etaMin);

        orders.byId(ord.id).ifPresent(o->o.status=OrderStatus.PICKED_UP);
        System.out.println("\nGET /orders/{id}/track -> " + api.getTrack(ord.id));

        assign.markDelivered(ord.id);
        System.out.println("\nDelivered. Track -> " + api.getTrack(ord.id));
    }
}
```

## Ride Sharing

```
/*
Template ->
1) define functional requirements
   - Rider requests a ride (pickup, drop, carType).
   - System matches nearest available driver; returns ETA & fare estimate.
   - Rider can confirm -> ride gets ACCEPTED; driver can start and end trip.
   - Pricing = base + perKm + perMin with simple surge (demand/supply).
   - Track ride: live status, driver location, ETA.
   - Payment confirmation (stub) after completion.
   - In-memory, single city, thread-safe where needed — doable in ~40 min.

2) define entities / actors
   Actors: Rider, Driver
   Entities: Rider, Driver(availability, loc), Ride(status lifecycle), Payment

3) define apis - get/post/put, request, response
   POST /riders                       {name} -> {riderId}
   POST /drivers                      {name, carType, lat, lon} -> {driverId}
   PUT  /drivers/{id}/location        {lat, lon, available} -> {ok}
   POST /rides/quote                  {riderId, pickup{lat,lon}, drop{lat,lon}, carType} -> {quoteId, driverId, etaMin, fareEstimate}
   POST /rides/confirm                {quoteId} -> {rideId, status}
   POST /rides/{rideId}/start         {} -> {status}
   POST /rides/{rideId}/end           {} -> {fare, status}
   POST /payments                     {rideId, method, txnRef?} -> {paymentId, status}
   GET  /rides/{rideId}/track         -> {status, driverLoc, etaMin}

4) define services involved
   MatchingService     - nearest available driver by carType.
   PricingService      - distance, time estimate, fare + surge.
   RideService         - create/confirm/start/end rides, state machine.
   DriverService       - update location/availability.
   PaymentService      - confirm payments (stub).
   TrackingService     - ETA/status view.
   IdGenerator         - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   rider(id PK, name, created_at)
   driver(id PK, name, car_type, lat, lon, available BOOL, rating)
   ride(id PK, rider_id FK, driver_id FK, pickup_lat, pickup_lon, drop_lat, drop_lon, car_type, 
        requested_at, accepted_at, started_at, ended_at, distance_km, duration_min, fare, status)
   payment(id PK, ride_id FK UNIQUE, method, amount, status, txn_ref, paid_at)
*/
```

### Java Implementation

```java
/*
Template ->
1) define functional requirements
   - Rider requests a ride (pickup, drop, carType).
   - System matches nearest available driver; returns ETA & fare estimate.
   - Rider can confirm -> ride gets ACCEPTED; driver can start and end trip.
   - Pricing = base + perKm + perMin with simple surge (demand/supply).
   - Track ride: live status, driver location, ETA.
   - Payment confirmation (stub) after completion.
   - In-memory, single city, thread-safe where needed — doable in ~40 min.

2) define entities / actors
   Actors: Rider, Driver
   Entities: Rider, Driver(availability, loc), Ride(status lifecycle), Payment

3) define apis - get/post/put, request, response
   POST /riders                       {name} -> {riderId}
   POST /drivers                      {name, carType, lat, lon} -> {driverId}
   PUT  /drivers/{id}/location        {lat, lon, available} -> {ok}
   POST /rides/quote                  {riderId, pickup{lat,lon}, drop{lat,lon}, carType} -> {quoteId, driverId, etaMin, fareEstimate}
   POST /rides/confirm                {quoteId} -> {rideId, status}
   POST /rides/{rideId}/start         {} -> {status}
   POST /rides/{rideId}/end           {} -> {fare, status}
   POST /payments                     {rideId, method, txnRef?} -> {paymentId, status}
   GET  /rides/{rideId}/track         -> {status, driverLoc, etaMin}

4) define services involved
   MatchingService     - nearest available driver by carType.
   PricingService      - distance, time estimate, fare + surge.
   RideService         - create/confirm/start/end rides, state machine.
   DriverService       - update location/availability.
   PaymentService      - confirm payments (stub).
   TrackingService     - ETA/status view.
   IdGenerator         - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   rider(id PK, name, created_at)
   driver(id PK, name, car_type, lat, lon, available BOOL, rating)
   ride(id PK, rider_id FK, driver_id FK, pickup_lat, pickup_lon, drop_lat, drop_lon, car_type, 
        requested_at, accepted_at, started_at, ended_at, distance_km, duration_min, fare, status)
   payment(id PK, ride_id FK UNIQUE, method, amount, status, txn_ref, paid_at)
*/

import java.time.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/* ===== Domain ===== */
enum CarType { MINI, SEDAN, SUV }
enum RideStatus { QUOTED, ACCEPTED, ONGOING, COMPLETED, CANCELLED }
enum PaymentStatus { PENDING, PAID, FAILED }

final class Geo { final double lat, lon; Geo(double lat,double lon){this.lat=lat;this.lon=lon;} }

final class Rider { final String id, name; final Instant createdAt=Instant.now(); Rider(String id,String n){this.id=id;this.name=n;} }
final class Driver {
    final String id, name; final CarType carType; volatile Geo loc; volatile boolean available=true; final double rating;
    Driver(String id,String n,CarType c,Geo l,double r){this.id=id;this.name=n;this.carType=c;this.loc=l;this.rating=r;}
}

final class Ride {
    final String id, riderId; String driverId;
    final CarType carType; final Geo pickup, drop;
    final Instant requestedAt=Instant.now();
    volatile Instant acceptedAt, startedAt, endedAt;
    volatile double distanceKm, durationMin, fare;
    volatile RideStatus status = RideStatus.QUOTED; // after quote; becomes ACCEPTED on confirm
    Ride(String id,String riderId,CarType carType,Geo pickup,Geo drop){
        this.id=id; this.riderId=riderId; this.carType=carType; this.pickup=pickup; this.drop=drop;
    }
}

final class Payment {
    final String id, rideId, method, txnRef; final double amount;
    volatile PaymentStatus status=PaymentStatus.PENDING; volatile Instant paidAt;
    Payment(String id,String rideId,String method,String txnRef,double amount){
        this.id=id; this.rideId=rideId; this.method=method; this.txnRef=txnRef; this.amount=amount;
    }
}

/* ===== Utils ===== */
class Ids { private final AtomicLong n=new AtomicLong(1); String next(String p){return p+"-"+n.getAndIncrement();} }
class Haversine {
    static double km(Geo a, Geo b){
        double R=6371, dLat=Math.toRadians(b.lat-a.lat), dLon=Math.toRadians(b.lon-a.lon);
        double s1=Math.sin(dLat/2), s2=Math.sin(dLon/2);
        double h=s1*s1 + Math.cos(Math.toRadians(a.lat))*Math.cos(Math.toRadians(b.lat))*s2*s2;
        return 2*R*Math.asin(Math.sqrt(h));
    }
}

/* ===== Repos (in-memory) ===== */
class RiderRepo { final Map<String,Rider> m=new ConcurrentHashMap<>(); Rider save(Rider x){m.put(x.id,x);return x;} Optional<Rider> byId(String id){return Optional.ofNullable(m.get(id));} }
class DriverRepo {
    final Map<String,Driver> m=new ConcurrentHashMap<>();
    Driver save(Driver d){m.put(d.id,d);return d;}
    Optional<Driver> byId(String id){return Optional.ofNullable(m.get(id));}
    List<Driver> availableByType(CarType t){ return m.values().stream().filter(d->d.available && d.carType==t).collect(Collectors.toList()); }
}
class RideRepo {
    final Map<String,Ride> m=new ConcurrentHashMap<>();
    Ride save(Ride r){m.put(r.id,r);return r;}
    Optional<Ride> byId(String id){return Optional.ofNullable(m.get(id));}
}
class PaymentRepo { final Map<String,Payment> m=new ConcurrentHashMap<>(); Payment save(Payment p){m.put(p.id,p);return p;} Optional<Payment> byRide(String rideId){return m.values().stream().filter(x->x.rideId.equals(rideId)).findFirst();} }

/* ===== Services ===== */
class DriverService {
    private final DriverRepo drivers;
    DriverService(DriverRepo d){drivers=d;}
    Driver register(String name, CarType type, double lat, double lon){
        Driver d = new Driver(Uber40Min.ids.next("drv"), name, type, new Geo(lat,lon), 4.7);
        return drivers.save(d);
    }
    void updateLocation(String driverId, double lat, double lon, boolean available){
        Driver d = drivers.byId(driverId).orElseThrow(()->new RuntimeException("driver"));
        d.loc = new Geo(lat,lon); d.available = available; drivers.save(d);
    }
}

class PricingService {
    // base fare per car type
    private static final Map<CarType,Double> BASE = Map.of(CarType.MINI,30.0, CarType.SEDAN,40.0, CarType.SUV,55.0);
    private static final Map<CarType,Double> PER_KM = Map.of(CarType.MINI,12.0, CarType.SEDAN,14.0, CarType.SUV,18.0);
    private static final Map<CarType,Double> PER_MIN= Map.of(CarType.MINI,1.5 , CarType.SEDAN,2.0 , CarType.SUV,2.5 );

    double surgeFactor(int demand, int supply){
        if (supply<=0) return 2.0;
        double ratio = (double)demand / supply; // >1 means surge
        return Math.min(2.5, Math.max(1.0, 1.0 + (ratio-1.0)*0.8)); // soft clamp
    }

    double estimateFare(CarType type, double km, double minutes, double surge){
        double fare = BASE.get(type) + PER_KM.get(type)*km + PER_MIN.get(type)*minutes;
        return round2(fare * surge);
    }
    static double round2(double v){ return Math.round(v*100.0)/100.0; }
}

class MatchingService {
    private final DriverRepo drivers;
    MatchingService(DriverRepo d){drivers=d;}
    Optional<Driver> nearest(CarType type, Geo pickup){
        return drivers.availableByType(type).stream()
                .min(Comparator.comparingDouble(d->Haversine.km(d.loc, pickup)));
    }
}

final class Quote {
    final String id, riderId; final CarType carType; final Geo pickup, drop;
    final String driverId; final int etaMin; final double fareEstimate;
    Quote(String id,String riderId,CarType carType,Geo p,Geo d,String driverId,int etaMin,double fare){
        this.id=id; this.riderId=riderId; this.carType=carType; this.pickup=p; this.drop=d; this.driverId=driverId; this.etaMin=etaMin; this.fareEstimate=fare;
    }
}

class RideService {
    private final RideRepo rides; private final DriverRepo drivers; private final MatchingService match; private final PricingService pricing;
    private final Map<String,Quote> quotes = new ConcurrentHashMap<>();

    RideService(RideRepo r, DriverRepo d, MatchingService m, PricingService p){rides=r;drivers=d;match=m;pricing=p;}

    Quote quote(String riderId, CarType type, Geo pickup, Geo drop){
        // naive ETA: distance from driver to pickup at 22km/h
        Optional<Driver> cand = match.nearest(type, pickup);
        if (cand.isEmpty()) throw new RuntimeException("no driver available");
        Driver drv = cand.get();
        double distToPickupKm = Haversine.km(drv.loc, pickup);
        int etaMin = Math.max(2, (int)Math.round(distToPickupKm / 0.37)); // ~22 km/h

        // trip distance & duration estimate
        double tripKm = Haversine.km(pickup, drop) * 1.2; // 20% road factor
        double minutes = Math.max(10, tripKm / 0.35);     // ~21 km/h avg

        // surge factor from simple demand/supply around car type
        int demand=1; int supply = drivers.availableByType(type).size();
        double surge = pricing.surgeFactor(demand, supply);
        double estimate = pricing.estimateFare(type, tripKm, minutes, surge);

        String qid = Uber40Min.ids.next("quote");
        Quote q = new Quote(qid, riderId, type, pickup, drop, drv.id, etaMin, estimate);
        quotes.put(qid, q);
        return q;
    }

    synchronized Ride confirm(String quoteId){
        Quote q = Optional.ofNullable(quotes.remove(quoteId)).orElseThrow(()->new RuntimeException("quote expired"));
        Driver d = drivers.byId(q.driverId).orElseThrow(()->new RuntimeException("driver missing"));
        if (!d.available) throw new RuntimeException("driver just got busy");
        d.available = false; drivers.save(d);

        Ride ride = new Ride(Uber40Min.ids.next("ride"), q.riderId, q.carType, q.pickup, q.drop);
        ride.driverId = q.driverId;
        ride.acceptedAt = Instant.now();
        ride.status = RideStatus.ACCEPTED;
        return rides.save(ride);
    }

    synchronized Ride start(String rideId){
        Ride r = rides.byId(rideId).orElseThrow(()->new RuntimeException("ride"));
        if (r.status != RideStatus.ACCEPTED) throw new RuntimeException("not ready to start");
        r.startedAt = Instant.now(); r.status = RideStatus.ONGOING;
        return rides.save(r);
    }

    synchronized Ride end(String rideId){
        Ride r = rides.byId(rideId).orElseThrow(()->new RuntimeException("ride"));
        if (r.status != RideStatus.ONGOING) throw new RuntimeException("not ongoing");
        r.endedAt = Instant.now();
        // compute actuals (in demo use straight estimates)
        double tripKm = Haversine.km(r.pickup, r.drop) * 1.2;
        double minutes = Math.max(10, Duration.between(r.startedAt, r.endedAt).toMinutes());
        double surge = 1.0;
        r.distanceKm = round2(tripKm); r.durationMin = round2(minutes);
        r.fare = PricingService.round2(new PricingService().estimateFare(r.carType, tripKm, minutes, surge));
        r.status = RideStatus.COMPLETED;
        rides.save(r);

        // free driver
        Driver d = drivers.byId(r.driverId).orElseThrow();
        d.available = true; drivers.save(d);
        return r;
    }

    private static double round2(double v){ return Math.round(v*100.0)/100.0; }
}

class PaymentService {
    private final PaymentRepo payments; PaymentService(PaymentRepo p){payments=p;}
    Payment confirm(String rideId, double amount, String method, String txnRef){
        Payment pay = new Payment(Uber40Min.ids.next("pay"), rideId, method, txnRef, amount);
        pay.status = PaymentStatus.PAID; pay.paidAt = Instant.now();
        return payments.save(pay);
    }
}

class TrackingService {
    private final RideRepo rides; private final DriverRepo drivers;
    TrackingService(RideRepo r, DriverRepo d){rides=r;drivers=d;}
    Map<String,Object> track(String rideId){
        Ride ride = rides.byId(rideId).orElseThrow(()->new RuntimeException("ride"));
        Map<String,Object> m = new LinkedHashMap<>();
        m.put("status", ride.status.name());
        if (ride.driverId!=null){
            Driver d = drivers.byId(ride.driverId).orElse(null);
            if (d!=null) {
                m.put("driverId", d.id);
                m.put("driverLoc", Map.of("lat", d.loc.lat, "lon", d.loc.lon));
                int eta = ride.status==RideStatus.ACCEPTED ? Math.max(2,(int)Math.round(Haversine.km(d.loc, ride.pickup)/0.37)) :
                          ride.status==RideStatus.ONGOING  ? Math.max(2,(int)Math.round(Haversine.km(d.loc, ride.drop)/0.37)) : 0;
                m.put("etaMin", eta);
            }
        }
        return m;
    }
}

/* ===== Controller Facade (mirrors APIs) ===== */
class UberController {
    private final DriverService driverSvc; private final RideService rideSvc; private final PricingService pricing;
    private final PaymentService paySvc; private final TrackingService tracking;

    UberController(DriverService d, RideService r, PricingService p, PaymentService pay, TrackingService t){
        driverSvc=d; rideSvc=r; pricing=p; paySvc=pay; tracking=t;
    }

    Rider postRider(RiderRepo riders, String name){ Rider r = new Rider(Uber40Min.ids.next("r"), name); return riders.save(r); }
    Driver postDriver(String name, CarType type, double lat, double lon){ return driverSvc.register(name, type, lat, lon); }
    void putDriverLocation(String driverId, double lat, double lon, boolean available){ driverSvc.updateLocation(driverId, lat, lon, available); }

    Quote postQuote(String riderId, CarType type, Geo pickup, Geo drop){ return rideSvc.quote(riderId, type, pickup, drop); }
    Ride postConfirm(String quoteId){ return rideSvc.confirm(quoteId); }
    Ride postStart(String rideId){ return rideSvc.start(rideId); }
    Ride postEnd(String rideId){ return rideSvc.end(rideId); }
    Payment postPayment(String rideId, double amount, String method, String txnRef){ return paySvc.confirm(rideId, amount, method, txnRef); }
    Map<String,Object> getTrack(String rideId){ return tracking.track(rideId); }
}

/* ===== Demo (tiny, 40-min friendly) ===== */
public class Uber40Min {
    static final Ids ids = new Ids();

    public static void main(String[] args) throws InterruptedException {
        // Repos
        RiderRepo riders = new RiderRepo();
        DriverRepo drivers = new DriverRepo();
        RideRepo rideRepo = new RideRepo();
        PaymentRepo payRepo = new PaymentRepo();

        // Services
        DriverService driverSvc = new DriverService(drivers);
        PricingService pricing = new PricingService();
        MatchingService matcher = new MatchingService(drivers);
        RideService rideSvc = new RideService(rideRepo, drivers, matcher, pricing);
        PaymentService paySvc = new PaymentService(payRepo);
        TrackingService tracking = new TrackingService(rideRepo, drivers);

        UberController api = new UberController(driverSvc, rideSvc, pricing, paySvc, tracking);

        // Seed riders & drivers
        Rider r1 = api.postRider(riders, "Aarav");
        Driver d1 = api.postDriver("Ravi", CarType.SEDAN, 12.912, 77.641);
        Driver d2 = api.postDriver("Kiran", CarType.SEDAN, 12.915, 77.63);
        Driver d3 = api.postDriver("Rohit", CarType.MINI , 12.90 , 77.62);

        // Rider requests a quote (SEDAN)
        Geo pickup = new Geo(12.914, 77.638);
        Geo drop   = new Geo(12.935, 77.624);
        Quote q = api.postQuote(r1.id, CarType.SEDAN, pickup, drop);
        System.out.println("QUOTE -> driver="+q.driverId+" etaMin="+q.etaMin+" fareEst="+q.fareEstimate);

        // Rider confirms
        Ride ride = api.postConfirm(q.id);
        System.out.println("CONFIRM -> rideId="+ride.id+" status="+ride.status);

        System.out.println("TRACK pre-start -> "+api.getTrack(ride.id));
        api.postStart(ride.id);
        System.out.println("START -> status="+rideRepo.byId(ride.id).get().status);

        // Simulate driving...
        Thread.sleep(1000);
        api.putDriverLocation(ride.driverId, 12.925, 77.63, false);
        System.out.println("TRACK mid -> "+api.getTrack(ride.id));

        // End ride
        Ride ended = api.postEnd(ride.id);
        System.out.println("END -> fare="+ended.fare+" status="+ended.status);

        // Payment
        Payment pay = api.postPayment(ride.id, ended.fare, "UPI", "TXN-7788");
        System.out.println("PAYMENT -> "+pay.status+" amount="+pay.amount);
    }
}
```

## Chat App

```
/*
Template ->
1) define functional requirements
   - One-to-one and group chats.
   - Send/receive text messages; mark as delivered/read.
   - Fetch chat history with pagination (cursor/limit).
   - Maintain online/offline status.
   - Simple in-memory pub-sub style notifications (stub).
   - Lightweight, concurrency-safe where needed; doable in ~40 min.

2) define entities / actors
   Actors: User
   Entities: User, Chat (1-1 or group), Message, Participant, Presence

3) define apis - get/post/put, request, response
   POST   /users                        {name} -> {userId}
   POST   /chats                        {creatorId, participantIds:[...], groupName?} -> {chatId}
   POST   /chats/{chatId}/messages      {senderId, text} -> {messageId, ts}
   GET    /chats/{chatId}/messages      {cursor?, limit} -> [{messageId, senderId, text, ts, status}]
   PUT    /messages/{id}/delivered      {userId} -> {ok}
   PUT    /messages/{id}/read           {userId} -> {ok}
   PUT    /users/{id}/presence          {online} -> {ok}

4) define services involved
   UserService       - create users, update presence.
   ChatService       - create chat, add participants.
   MessageService    - send messages, mark delivered/read.
   HistoryService    - fetch chat history with pagination.
   NotificationService- stub for notifying participants.
   IdGenerator       - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, online BOOL, created_at)
   chat(id PK, group_name NULL, is_group BOOL, created_at)
   chat_participant(chat_id FK, user_id FK, joined_at)
   message(id PK, chat_id FK, sender_id FK, text, created_at, status ENUM)
   message_status(message_id FK, user_id FK, delivered_at, read_at)
*/
```

### Java Implementation

```java
/*
Template ->
1) define functional requirements
   - One-to-one and group chats.
   - Send/receive text messages; mark as delivered/read.
   - Fetch chat history with pagination (cursor/limit).
   - Maintain online/offline status.
   - Simple in-memory pub-sub style notifications (stub).
   - Lightweight, concurrency-safe where needed; doable in ~40 min.

2) define entities / actors
   Actors: User
   Entities: User, Chat (1-1 or group), Message, Participant, Presence

3) define apis - get/post/put, request, response
   POST   /users                        {name} -> {userId}
   POST   /chats                        {creatorId, participantIds:[...], groupName?} -> {chatId}
   POST   /chats/{chatId}/messages      {senderId, text} -> {messageId, ts}
   GET    /chats/{chatId}/messages      {cursor?, limit} -> [{messageId, senderId, text, ts, status}]
   PUT    /messages/{id}/delivered      {userId} -> {ok}
   PUT    /messages/{id}/read           {userId} -> {ok}
   PUT    /users/{id}/presence          {online} -> {ok}

4) define services involved
   UserService       - create users, update presence.
   ChatService       - create chat, add participants.
   MessageService    - send messages, mark delivered/read.
   HistoryService    - fetch chat history with pagination.
   NotificationService- stub for notifying participants.
   IdGenerator       - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, online BOOL, created_at)
   chat(id PK, group_name NULL, is_group BOOL, created_at)
   chat_participant(chat_id FK, user_id FK, joined_at)
   message(id PK, chat_id FK, sender_id FK, text, created_at, status ENUM)
   message_status(message_id FK, user_id FK, delivered_at, read_at)
*/

import java.time.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/* ===== Domain ===== */
enum MessageStatus { SENT, DELIVERED, READ }

final class User { final String id,name; volatile boolean online=false; final Instant createdAt=Instant.now(); User(String id,String n){this.id=id;this.name=n;} }
final class Chat { final String id, groupName; final boolean isGroup; final Set<String> participants=new HashSet<>(); final Instant createdAt=Instant.now();
    Chat(String id,boolean isGroup,String groupName){this.id=id;this.isGroup=isGroup;this.groupName=groupName;}
}
final class Message {
    final String id, chatId, senderId, text; final Instant createdAt=Instant.now();
    final Map<String,MessageStatus> perUser=new ConcurrentHashMap<>(); // userId -> status
    Message(String id,String chatId,String senderId,String text){this.id=id;this.chatId=chatId;this.senderId=senderId;this.text=text;}
}

/* ===== Utils ===== */
class Ids { private final AtomicLong n=new AtomicLong(1); String next(String p){return p+"-"+n.getAndIncrement();} }

/* ===== Repos ===== */
class UserRepo { final Map<String,User> m=new ConcurrentHashMap<>(); User save(User u){m.put(u.id,u);return u;} Optional<User> byId(String id){return Optional.ofNullable(m.get(id));} }
class ChatRepo { final Map<String,Chat> m=new ConcurrentHashMap<>(); Chat save(Chat c){m.put(c.id,c);return c;} Optional<Chat> byId(String id){return Optional.ofNullable(m.get(id));} }
class MsgRepo { final Map<String,Message> m=new ConcurrentHashMap<>(); Message save(Message x){m.put(x.id,x);return x;} Optional<Message> byId(String id){return Optional.ofNullable(m.get(id));} List<Message> byChat(String chatId){return m.values().stream().filter(m->m.chatId.equals(chatId)).sorted(Comparator.comparing((Message x)->x.createdAt)).collect(Collectors.toList());} }

/* ===== Services ===== */
class UserService {
    private final UserRepo users; private final Ids ids;
    UserService(UserRepo u,Ids ids){users=u;this.ids=ids;}
    User create(String name){ return users.save(new User(ids.next("u"),name)); }
    void setPresence(String id, boolean online){ users.byId(id).ifPresent(u->u.online=online); }
}

class ChatService {
    private final ChatRepo chats; private final UserRepo users; private final Ids ids;
    ChatService(ChatRepo c,UserRepo u,Ids ids){chats=c;users=u;this.ids=ids;}
    Chat create(String creatorId, Set<String> parts, boolean isGroup, String groupName){
        Chat c = new Chat(ids.next("chat"),isGroup,groupName);
        c.participants.add(creatorId); c.participants.addAll(parts);
        return chats.save(c);
    }
}

class MessageService {
    private final MsgRepo msgs; private final ChatRepo chats; private final Ids ids;
    MessageService(MsgRepo m,ChatRepo c,Ids ids){msgs=m;chats=c;this.ids=ids;}
    Message send(String chatId,String senderId,String text){
        Chat c=chats.byId(chatId).orElseThrow(()->new RuntimeException("chat not found"));
        if(!c.participants.contains(senderId)) throw new RuntimeException("not in chat");
        Message m=new Message(ids.next("msg"),chatId,senderId,text);
        for(String uid:c.participants){ m.perUser.put(uid, uid.equals(senderId)?MessageStatus.READ:MessageStatus.SENT); }
        return msgs.save(m);
    }
    void delivered(String msgId,String userId){ Message m=msgs.byId(msgId).orElseThrow(); m.perUser.put(userId,MessageStatus.DELIVERED); }
    void read(String msgId,String userId){ Message m=msgs.byId(msgId).orElseThrow(); m.perUser.put(userId,MessageStatus.READ); }
}

class HistoryService {
    private final MsgRepo msgs;
    HistoryService(MsgRepo m){msgs=m;}
    List<Message> getHistory(String chatId, String cursor, int limit){
        List<Message> all=msgs.byChat(chatId);
        int start=0;
        if(cursor!=null){
            for(int i=0;i<all.size();i++){ if(all.get(i).id.equals(cursor)){ start=i+1; break; } }
        }
        return all.stream().skip(start).limit(limit).collect(Collectors.toList());
    }
}

/* ===== Controller ===== */
class ChatController {
    private final UserService users; private final ChatService chats; private final MessageService msgs; private final HistoryService history;
    ChatController(UserService u,ChatService c,MessageService m,HistoryService h){users=u;chats=c;msgs=m;history=h;}

    User postUser(String name){ return users.create(name); }
    void putPresence(String id, boolean online){ users.setPresence(id,online); }

    Chat postChat(String creatorId, Set<String> parts, boolean isGroup, String groupName){ return chats.create(creatorId,parts,isGroup,groupName); }

    Message postMessage(String chatId,String senderId,String text){ return msgs.send(chatId,senderId,text); }
    void putDelivered(String msgId,String userId){ msgs.delivered(msgId,userId); }
    void putRead(String msgId,String userId){ msgs.read(msgId,userId); }

    List<Message> getHistory(String chatId,String cursor,int limit){ return history.getHistory(chatId,cursor,limit); }
}

/* ===== Demo ===== */
public class WhatsApp40Min {
    public static void main(String[] args) {
        Ids ids=new Ids(); UserRepo userRepo=new UserRepo(); ChatRepo chatRepo=new ChatRepo(); MsgRepo msgRepo=new MsgRepo();
        UserService userSvc=new UserService(userRepo,ids);
        ChatService chatSvc=new ChatService(chatRepo,userRepo,ids);
        MessageService msgSvc=new MessageService(msgRepo,chatRepo,ids);
        HistoryService histSvc=new HistoryService(msgRepo);
        ChatController api=new ChatController(userSvc,chatSvc,msgSvc,histSvc);

        User a=api.postUser("Alice"), b=api.postUser("Bob");
        api.putPresence(a.id,true); api.putPresence(b.id,true);

        Chat chat=api.postChat(a.id,Set.of(b.id),false,null);
        System.out.println("Chat created: "+chat.id);

        Message m1=api.postMessage(chat.id,a.id,"Hi Bob!");
        Message m2=api.postMessage(chat.id,b.id,"Hey Alice!");
        api.putDelivered(m1.id,b.id); api.putRead(m1.id,b.id);

        System.out.println("History: ");
        for(Message m: api.getHistory(chat.id,null,10)){
            System.out.println(m.id+" from "+m.senderId+": "+m.text+" statuses="+m.perUser);
        }
    }
}
```

## File Store

```
/*
Template ->
1) define functional requirements
   - Create folders/files; hierarchical tree with root per user.
   - Upload file (new file or new version), download (stub returns bytes length), rename, move, delete (trash) & restore.
   - Share file/folder with users with permissions: VIEW, EDIT, OWNER (owner implicit).
   - List folder contents with pagination (cursor+limit).
   - Search by name (prefix/substring) within items user can access.
   - Version history: list versions, restore a previous version.
   - In-memory only; 40-min interview friendly; single JVM; basic concurrency safety.

2) define entities / actors
   Actors: User
   Entities: User, Node(abstract), Folder, FileNode, FileVersion, ShareEntry, TrashEntry

3) define apis - get/post/put, request, response (mirrored by controller methods)
   POST   /users                                   {name} -> {userId}
   POST   /nodes/folder                            {ownerId, parentId, name} -> {folderId}
   POST   /nodes/file                              {ownerId, parentId, name, bytes[]} -> {fileId, versionId}
   POST   /nodes/file/{fileId}/versions            {ownerId, bytes[]} -> {versionId}
   GET    /nodes/{nodeId}                          -> {metadata}
   GET    /nodes/{folderId}/children               {cursor?, limit} -> {items[], nextCursor?}
   GET    /download/{fileId}/latest                -> {bytesLength, versionId}
   POST   /share                                   {nodeId, granteeUserId, perm(VIEW|EDIT)} -> {ok}
   GET    /search                                  {userId, query} -> {nodes[]}
   PUT    /nodes/{nodeId}/rename                   {name} -> {ok}
   PUT    /nodes/{nodeId}/move                     {newParentId} -> {ok}
   DELETE /nodes/{nodeId}                          -> {trashed=true}
   POST   /trash/{nodeId}/restore                  -> {ok}
   GET    /files/{fileId}/versions                 -> [{versionId, size, createdAt}]
   POST   /files/{fileId}/restoreVersion           {versionId} -> {ok}

4) define services involved
   AuthZService        - permission checks (OWNER/EDIT/VIEW), inheritance on folders.
   TreeService         - create/move/rename/list; trash/restore; path integrity.
   FileService         - upload versions, download, version list/restore.
   ShareService        - grant/revoke sharing on nodes (propagates by traversal).
   SearchService       - simple name-based search filtered by access.
   IdGenerator         - IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, created_at)
   node(id PK, type ENUM(FILE,FOLDER), name, owner_id FK(user), parent_id FK(node), created_at, updated_at, trashed BOOL)
   file_version(id PK, file_id FK(node), size, created_at, data BLOB)   // in prod, data in object store
   share(node_id FK, grantee_user_id FK(user), perm ENUM(VIEW,EDIT), created_at)  UNIQUE(node_id, grantee_user_id)
   // effective permission = owner OR explicit share OR inherited from any ancestor folder
*/
```

### Java Implementation

```java
/*
Template ->
1) define functional requirements
   - Create folders/files; hierarchical tree with root per user.
   - Upload file (new file or new version), download (stub returns bytes length), rename, move, delete (trash) & restore.
   - Share file/folder with users with permissions: VIEW, EDIT, OWNER (owner implicit).
   - List folder contents with pagination (cursor+limit).
   - Search by name (prefix/substring) within items user can access.
   - Version history: list versions, restore a previous version.
   - In-memory only; 40-min interview friendly; single JVM; basic concurrency safety.

2) define entities / actors
   Actors: User
   Entities: User, Node(abstract), Folder, FileNode, FileVersion, ShareEntry, TrashEntry

3) define apis - get/post/put, request, response (mirrored by controller methods)
   POST   /users                                   {name} -> {userId}
   POST   /nodes/folder                            {ownerId, parentId, name} -> {folderId}
   POST   /nodes/file                              {ownerId, parentId, name, bytes[]} -> {fileId, versionId}
   POST   /nodes/file/{fileId}/versions            {ownerId, bytes[]} -> {versionId}
   GET    /nodes/{nodeId}                          -> {metadata}
   GET    /nodes/{folderId}/children               {cursor?, limit} -> {items[], nextCursor?}
   GET    /download/{fileId}/latest                -> {bytesLength, versionId}
   POST   /share                                   {nodeId, granteeUserId, perm(VIEW|EDIT)} -> {ok}
   GET    /search                                  {userId, query} -> {nodes[]}
   PUT    /nodes/{nodeId}/rename                   {name} -> {ok}
   PUT    /nodes/{nodeId}/move                     {newParentId} -> {ok}
   DELETE /nodes/{nodeId}                          -> {trashed=true}
   POST   /trash/{nodeId}/restore                  -> {ok}
   GET    /files/{fileId}/versions                 -> [{versionId, size, createdAt}]
   POST   /files/{fileId}/restoreVersion           {versionId} -> {ok}

4) define services involved
   AuthZService        - permission checks (OWNER/EDIT/VIEW), inheritance on folders.
   TreeService         - create/move/rename/list; trash/restore; path integrity.
   FileService         - upload versions, download, version list/restore.
   ShareService        - grant/revoke sharing on nodes (propagates by traversal).
   SearchService       - simple name-based search filtered by access.
   IdGenerator         - IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, created_at)
   node(id PK, type ENUM(FILE,FOLDER), name, owner_id FK(user), parent_id FK(node), created_at, updated_at, trashed BOOL)
   file_version(id PK, file_id FK(node), size, created_at, data BLOB)   // in prod, data in object store
   share(node_id FK, grantee_user_id FK(user), perm ENUM(VIEW,EDIT), created_at)  UNIQUE(node_id, grantee_user_id)
   // effective permission = owner OR explicit share OR inherited from any ancestor folder
*/

import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/* ===== Domain ===== */
enum NodeType { FILE, FOLDER }
enum Perm { VIEW, EDIT, OWNER }

final class User { final String id, name; final Instant createdAt=Instant.now(); User(String id,String name){this.id=id;this.name=name;} }

/** Abstract Node */
abstract class Node {
    final String id, ownerId;
    volatile String parentId; // null for root
    volatile String name;
    final NodeType type;
    volatile boolean trashed=false;
    volatile Instant createdAt=Instant.now(), updatedAt=Instant.now();
    Node(String id,String ownerId,String parentId,String name,NodeType type){
        this.id=id; this.ownerId=ownerId; this.parentId=parentId; this.name=name; this.type=type;
    }
}
final class Folder extends Node { Folder(String id,String ownerId,String parentId,String name){ super(id,ownerId,parentId,name,NodeType.FOLDER);} }

final class FileVersion {
    final String id; final String fileId;
    final byte[] data; final int size;
    final Instant createdAt=Instant.now();
    FileVersion(String id,String fileId,byte[] data){
        this.id=id; this.fileId=fileId; this.data=data; this.size=data.length;
    }
}
final class FileNode extends Node {
    // versions newest-first at index 0
    final List<FileVersion> versions = Collections.synchronizedList(new ArrayList<>());
    FileNode(String id,String ownerId,String parentId,String name){ super(id,ownerId,parentId,name,NodeType.FILE); }
}

final class ShareEntry {
    final String nodeId; final String granteeUserId; final Perm perm; final Instant createdAt=Instant.now();
    ShareEntry(String nodeId,String granteeUserId,Perm perm){this.nodeId=nodeId;this.granteeUserId=granteeUserId;this.perm=perm;}
}

/* ===== Ids ===== */
class Ids { private final AtomicLong n=new AtomicLong(1); String next(String p){ return p+"-"+n.getAndIncrement(); } }

/* ===== Repos (in-memory) ===== */
class UserRepo { final Map<String,User> m=new ConcurrentHashMap<>(); User save(User u){m.put(u.id,u);return u;} Optional<User> byId(String id){return Optional.ofNullable(m.get(id));} }
class NodeRepo {
    final Map<String,Node> m=new ConcurrentHashMap<>();
    Node save(Node n){ n.updatedAt=Instant.now(); m.put(n.id,n); return n; }
    Optional<Node> byId(String id){ return Optional.ofNullable(m.get(id)); }
    List<Node> children(String parentId){
        return m.values().stream()
                .filter(n->Objects.equals(n.parentId,parentId))
                .sorted(Comparator.comparing((Node x)->x.type).thenComparing(x->x.name.toLowerCase()))
                .collect(Collectors.toList());
    }
}
class VersionRepo {
    final Map<String,FileVersion> m=new ConcurrentHashMap<>();
    FileVersion save(FileVersion v){ m.put(v.id,v); return v; }
    Optional<FileVersion> byId(String id){ return Optional.ofNullable(m.get(id)); }
}
class ShareRepo {
    // key: nodeId -> (userId -> perm)
    final Map<String, Map<String, ShareEntry>> m = new ConcurrentHashMap<>();
    void upsert(String nodeId, String userId, Perm perm){
        m.computeIfAbsent(nodeId,k->new ConcurrentHashMap<>()).put(userId, new ShareEntry(nodeId,userId,perm));
    }
    Optional<ShareEntry> get(String nodeId, String userId){
        return Optional.ofNullable(m.getOrDefault(nodeId, Map.of()).get(userId));
    }
    Map<String,ShareEntry> forNode(String nodeId){ return m.getOrDefault(nodeId, Map.of()); }
}

/* ===== Exceptions ===== */
class DomainException extends RuntimeException { DomainException(String msg){super(msg);} }

/* ===== Services ===== */
class AuthZService {
    private final NodeRepo nodes; private final ShareRepo shares;
    AuthZService(NodeRepo n, ShareRepo s){nodes=n; shares=s;}

    boolean canView(String userId, String nodeId){ return hasPerm(userId,nodeId,Perm.VIEW); }
    boolean canEdit(String userId, String nodeId){ return hasPerm(userId,nodeId,Perm.EDIT); }

    private boolean hasPerm(String userId, String nodeId, Perm needed){
        Node cur = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        // owner is OWNER
        if (cur.ownerId.equals(userId)) return true;
        // explicit share
        Perm max = maxPermOnNode(userId, cur.id);
        if (permSatisfies(max, needed)) return true;
        // inherited from ancestors
        String pid = cur.parentId;
        while (pid != null){
            Node parent = nodes.byId(pid).orElse(null);
            if (parent==null) break;
            max = maxPermOnNode(userId, parent.id);
            if (permSatisfies(max, needed)) return true;
            pid = parent.parentId;
        }
        return false;
    }

    private Perm maxPermOnNode(String userId, String nodeId){
        return shares.get(nodeId,userId).map(e->e.perm).orElse(null);
    }

    private boolean permSatisfies(Perm have, Perm needed){
        if (have==null) return false;
        if (have==Perm.OWNER) return true;
        if (needed==Perm.VIEW) return have==Perm.VIEW || have==Perm.EDIT;
        if (needed==Perm.EDIT) return have==Perm.EDIT; // OWNER already handled
        return false;
    }
}

class TreeService {
    private final NodeRepo nodes; private final Ids ids;
    TreeService(NodeRepo n, Ids ids){nodes=n; this.ids=ids;}

    synchronized Folder createFolder(String ownerId, String parentId, String name){
        validateParent(parentId, ownerId);
        Folder f = new Folder(ids.next("fld"), ownerId, parentId, name);
        return (Folder) nodes.save(f);
    }

    synchronized FileNode createFile(String ownerId, String parentId, String name, byte[] data, VersionRepo versions){
        validateParent(parentId, ownerId);
        FileNode fn = new FileNode(ids.next("fil"), ownerId, parentId, name);
        nodes.save(fn);
        // first version
        FileVersion v = new FileVersion(ids.next("ver"), fn.id, data);
        versions.save(v);
        fn.versions.add(0, v);
        return (FileNode) nodes.save(fn);
    }

    synchronized void rename(String userId, String nodeId, String newName){
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        if (!n.ownerId.equals(userId)) throw new DomainException("only owner can rename (simplified)");
        n.name = newName; nodes.save(n);
    }

    synchronized void move(String userId, String nodeId, String newParentId){
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        Node p = newParentId==null?null:nodes.byId(newParentId).orElseThrow(()->new DomainException("parent"));
        if (p!=null && p.type!=NodeType.FOLDER) throw new DomainException("parent must be folder");
        if (!n.ownerId.equals(userId)) throw new DomainException("only owner can move (simplified)");
        // prevent cycles
        if (isDescendant(newParentId, n.id)) throw new DomainException("cannot move into descendant");
        n.parentId = newParentId; nodes.save(n);
    }

    synchronized void trash(String userId, String nodeId){
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        if (!n.ownerId.equals(userId)) throw new DomainException("only owner can trash");
        markTrashedRecursive(n, true);
    }

    synchronized void restore(String userId, String nodeId){
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        if (!n.ownerId.equals(userId)) throw new DomainException("only owner can restore");
        markTrashedRecursive(n, false);
    }

    List<Node> listChildren(String folderId, String cursor, int limit){
        Node f = nodes.byId(folderId).orElseThrow(()->new DomainException("folder"));
        if (f.type!=NodeType.FOLDER) throw new DomainException("not folder");
        List<Node> all = nodes.children(folderId).stream().filter(n->!n.trashed).collect(Collectors.toList());
        int start = 0;
        if (cursor!=null){
            for (int i=0;i<all.size();i++) if (all.get(i).id.equals(cursor)) { start = i+1; break; }
        }
        return all.stream().skip(start).limit(limit).collect(Collectors.toList());
    }

    private void validateParent(String parentId, String ownerId){
        if (parentId==null) return;
        Node p = nodes.byId(parentId).orElseThrow(()->new DomainException("parent not found"));
        if (p.type!=NodeType.FOLDER) throw new DomainException("parent must be a folder");
        if (!p.ownerId.equals(ownerId)) throw new DomainException("parent not owned by creator (simplified)");
    }

    private boolean isDescendant(String candidateParentId, String nodeId){
        String cur = candidateParentId;
        while (cur!=null){
            if (cur.equals(nodeId)) return true;
            Node n = nodes.byId(cur).orElse(null);
            cur = n==null?null:n.parentId;
        }
        return false;
    }

    private void markTrashedRecursive(Node n, boolean val){
        n.trashed = val; nodes.save(n);
        if (n.type==NodeType.FOLDER){
            for (Node c : nodes.children(n.id)) markTrashedRecursive(c, val);
        }
    }
}

class FileService {
    private final NodeRepo nodes; private final VersionRepo versions; private final Ids ids;
    FileService(NodeRepo n, VersionRepo v, Ids ids){nodes=n; versions=v; this.ids=ids;}

    FileVersion uploadNewVersion(String userId, String fileId, byte[] data){
        FileNode f = (FileNode) nodes.byId(fileId).orElseThrow(()->new DomainException("file"));
        if (!f.ownerId.equals(userId)) throw new DomainException("only owner can upload version (simplified)");
        FileVersion v = new FileVersion(ids.next("ver"), f.id, data);
        versions.save(v);
        f.versions.add(0, v);
        nodes.save(f);
        return v;
    }

    FileVersion downloadLatest(String userId, String fileId){
        FileNode f = (FileNode) nodes.byId(fileId).orElseThrow(()->new DomainException("file"));
        if (f.versions.isEmpty()) throw new DomainException("no versions");
        return f.versions.get(0);
    }

    List<FileVersion> listVersions(String fileId){
        FileNode f = (FileNode) nodes.byId(fileId).orElseThrow(()->new DomainException("file"));
        return new ArrayList<>(f.versions);
    }

    void restoreVersion(String userId, String fileId, String versionId){
        FileNode f = (FileNode) nodes.byId(fileId).orElseThrow(()->new DomainException("file"));
        if (!f.ownerId.equals(userId)) throw new DomainException("only owner can restore");
        FileVersion v = versions.byId(versionId).orElseThrow(()->new DomainException("version"));
        if (!v.fileId.equals(f.id)) throw new DomainException("version/file mismatch");
        // move this version to head by inserting a clone (typical GDrive restore creates new head)
        FileVersion restored = new FileVersion(ids.next("ver"), f.id, v.data);
        versions.save(restored);
        f.versions.add(0, restored);
        nodes.save(f);
    }
}

class ShareService {
    private final ShareRepo shares; private final NodeRepo nodes;
    ShareService(ShareRepo s, NodeRepo n){shares=s; nodes=n;}
    void share(String ownerId, String nodeId, String granteeUserId, Perm perm){
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        if (!n.ownerId.equals(ownerId)) throw new DomainException("only owner can share (simplified)");
        if (perm==Perm.OWNER) throw new DomainException("cannot grant OWNER");
        shares.upsert(nodeId, granteeUserId, perm);
    }
}

class SearchService {
    private final NodeRepo nodes; private final AuthZService authz;
    SearchService(NodeRepo n, AuthZService a){nodes=n; authz=a;}
    List<Node> search(String userId, String query){
        String q = query.toLowerCase();
        return nodes.m.values().stream()
                .filter(n->!n.trashed)
                .filter(n->n.name.toLowerCase().contains(q))
                .filter(n->authz.canView(userId, n.id))
                .sorted(Comparator.comparing((Node n)->n.type).thenComparing(n->n.name.toLowerCase()))
                .collect(Collectors.toList());
    }
}

/* ===== Controller Facade ===== */
class DriveController {
    private final UserRepo users; private final NodeRepo nodes; private final VersionRepo versions;
    private final AuthZService authz; private final TreeService tree; private final FileService fileSvc;
    private final ShareService share; private final SearchService search;

    DriveController(UserRepo u, NodeRepo n, VersionRepo v, AuthZService a, TreeService t, FileService f, ShareService s, SearchService srch){
        users=u; nodes=n; versions=v; authz=a; tree=t; fileSvc=f; share=s; search=srch;
    }

    User postUser(String name){ return users.save(new User(GDrive40Min.ids.next("u"), name)); }

    Folder postFolder(String ownerId, String parentId, String name){ return tree.createFolder(ownerId, parentId, name); }

    FileNode postFile(String ownerId, String parentId, String name, byte[] data){ return tree.createFile(ownerId, parentId, name, data, versions); }

    FileVersion postFileVersion(String ownerId, String fileId, byte[] data){
        if (!authz.canEdit(ownerId, fileId)) throw new DomainException("no edit permission");
        return fileSvc.uploadNewVersion(ownerId, fileId, data);
    }

    Map<String,Object> getNode(String userId, String nodeId){
        if (!authz.canView(userId, nodeId)) throw new DomainException("no view permission");
        Node n = nodes.byId(nodeId).orElseThrow(()->new DomainException("node"));
        Map<String,Object> m = new LinkedHashMap<>();
        m.put("id", n.id); m.put("type", n.type.name()); m.put("name", n.name);
        m.put("ownerId", n.ownerId); m.put("parentId", n.parentId); m.put("trashed", n.trashed);
        return m;
    }

    Map<String,Object> getChildren(String userId, String folderId, String cursor, int limit){
        if (!authz.canView(userId, folderId)) throw new DomainException("no view permission");
        List<Node> items = tree.listChildren(folderId, cursor, limit);
        String next = items.size()==limit ? items.get(items.size()-1).id : null;
        Map<String,Object> out = new LinkedHashMap<>();
        out.put("items", items.stream().map(n->Map.of("id",n.id,"name",n.name,"type",n.type.name())).collect(Collectors.toList()));
        out.put("nextCursor", next);
        return out;
    }

    Map<String,Object> getDownloadLatest(String userId, String fileId){
        if (!authz.canView(userId, fileId)) throw new DomainException("no view permission");
        FileVersion v = fileSvc.downloadLatest(userId, fileId);
        return Map.of("versionId", v.id, "bytesLength", v.size);
    }

    void putRename(String userId, String nodeId, String newName){
        if (!authz.canEdit(userId, nodeId) && !nodes.byId(nodeId).orElseThrow().ownerId.equals(userId))
            throw new DomainException("no edit permission");
        tree.rename(userId, nodeId, newName);
    }

    void putMove(String userId, String nodeId, String newParentId){
        if (!nodes.byId(nodeId).orElseThrow().ownerId.equals(userId))
            throw new DomainException("only owner can move");
        tree.move(userId, nodeId, newParentId);
    }

    void deleteNode(String userId, String nodeId){
        if (!nodes.byId(nodeId).orElseThrow().ownerId.equals(userId))
            throw new DomainException("only owner can trash");
        tree.trash(userId, nodeId);
    }

    void postRestore(String userId, String nodeId){ tree.restore(userId, nodeId); }

    void postShare(String ownerId, String nodeId, String granteeUserId, Perm perm){ share.share(ownerId, nodeId, granteeUserId, perm); }

    List<Node> getSearch(String userId, String query){ return search.search(userId, query); }

    List<Map<String,Object>> getVersions(String userId, String fileId){
        if (!authz.canView(userId, fileId)) throw new DomainException("no view permission");
        return fileSvc.listVersions(fileId).stream().map(v->Map.of("versionId",v.id,"size",v.size,"createdAt",v.createdAt)).collect(Collectors.toList());
    }

    void postRestoreVersion(String ownerId, String fileId, String versionId){
        if (!authz.canEdit(ownerId, fileId)) throw new DomainException("no edit permission");
        fileSvc.restoreVersion(ownerId, fileId, versionId);
    }
}

/* ===== Demo (tiny, 40-min friendly) ===== */
public class GDrive40Min {
    static final Ids ids = new Ids();

    public static void main(String[] args) {
        // Repos
        UserRepo users = new UserRepo();
        NodeRepo nodes = new NodeRepo();
        VersionRepo versions = new VersionRepo();
        ShareRepo shares = new ShareRepo();

        // Services
        AuthZService authz = new AuthZService(nodes, shares);
        TreeService tree = new TreeService(nodes, ids);
        FileService fileSvc = new FileService(nodes, versions, ids);
        ShareService shareSvc = new ShareService(shares, nodes);
        SearchService searchSvc = new SearchService(nodes, authz);

        DriveController api = new DriveController(users, nodes, versions, authz, tree, fileSvc, shareSvc, searchSvc);

        // Users
        User alice = api.postUser("Alice");
        User bob   = api.postUser("Bob");

        // Root (null parent) and basic structure for Alice
        Folder root = api.postFolder(alice.id, null, "Alice Root");
        Folder docs = api.postFolder(alice.id, root.id, "Docs");
        Folder pics = api.postFolder(alice.id, root.id, "Pictures");

        // Upload a file
        FileNode spec = api.postFile(alice.id, docs.id, "DesignSpec.md", "v1 design".getBytes());
        System.out.println("Uploaded file: "+spec.id+" latest="+api.getDownloadLatest(alice.id, spec.id));

        // New version
        api.postFileVersion(alice.id, spec.id, "v2 design (added API)".getBytes());
        System.out.println("Versions: "+api.getVersions(alice.id, spec.id));

        // Share with Bob as VIEW
        api.postShare(alice.id, docs.id, bob.id, Perm.VIEW);

        // Bob lists Docs
        System.out.println("Bob children of Docs: "+api.getChildren(bob.id, docs.id, null, 10));

        // Search
        System.out.println("Search 'Design' as Bob: "+api.getSearch(bob.id, "Design"));

        // Rename & move (owner only)
        api.putRename(alice.id, spec.id, "DesignSpec_v2.md");
        api.putMove(alice.id, spec.id, pics.id);

        // Trash & restore
        api.deleteNode(alice.id, pics.id);
        System.out.println("After trash, children root: "+api.getChildren(alice.id, root.id, null, 10));
        api.postRestore(alice.id, pics.id);
        System.out.println("After restore, children root: "+api.getChildren(alice.id, root.id, null, 10));
    }
}
```

## Instagram Feed

```
/*
Template ->
1) define functional requirements
   - Users can follow/unfollow others.
   - Users create posts with media + caption; like/comment a post.
   - Generate home feed for a user from followed users’ posts.
   - Ranking = recency + lightweight engagement (likes/comments) signal.
   - Pagination with cursor (createdAt + postId).
   - Simple fan-out-on-read (compute feed on request), add basic cache with TTL.
   - In-memory, thread-safe where needed; doable in ~40 minutes.

2) define entities / actors
   Actors: User (viewer/creator)
   Entities: User, Post, Like, Comment, FollowEdge, FeedEntry (cached)

3) define apis - get/post/put, request, response
   POST   /users                             {username} -> {userId}
   POST   /users/{id}/follow                 {targetUserId} -> {status}
   DELETE /users/{id}/follow                 {targetUserId} -> {status}
   POST   /posts                             {authorId, caption, mediaUrl?} -> {postId}
   POST   /posts/{id}/like                   {userId} -> {likes}
   POST   /posts/{id}/comment                {userId, text} -> {commentId}
   GET    /feed                              {userId, cursor?, limit} -> {items:[...], nextCursor?}

4) define services involved
   UserService        - create users, follow/unfollow.
   PostService        - create posts; like/comment; read post stats.
   GraphService       - read follow graph (who I follow).
   FeedService        - build/rank/paginate feed; small cache with TTL.
   IdGenerator        - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, username UNIQUE, created_at)
   follow(user_id FK, target_user_id FK, created_at)  UNIQUE(user_id, target_user_id)
   post(id PK, author_id FK, caption, media_url, created_at)
   like(id PK, post_id FK, user_id FK, created_at)    UNIQUE(post_id, user_id)
   comment(id PK, post_id FK, user_id FK, text, created_at)
   (feed cache not persisted: user_id -> [post_id, score, cached_at])
*/
```

### Java Implementation

```java
/*
Template ->
1) define functional requirements
   - Users can follow/unfollow others.
   - Users create posts with media + caption; like/comment a post.
   - Generate home feed for a user from followed users’ posts.
   - Ranking = recency + lightweight engagement (likes/comments) signal.
   - Pagination with cursor (createdAt + postId).
   - Simple fan-out-on-read (compute feed on request), add basic cache with TTL.
   - In-memory, thread-safe where needed; doable in ~40 minutes.

2) define entities / actors
   Actors: User (viewer/creator)
   Entities: User, Post, Like, Comment, FollowEdge, FeedEntry (cached)

3) define apis - get/post/put, request, response
   POST   /users                             {username} -> {userId}
   POST   /users/{id}/follow                 {targetUserId} -> {status}
   DELETE /users/{id}/follow                 {targetUserId} -> {status}
   POST   /posts                             {authorId, caption, mediaUrl?} -> {postId}
   POST   /posts/{id}/like                   {userId} -> {likes}
   POST   /posts/{id}/comment                {userId, text} -> {commentId}
   GET    /feed                              {userId, cursor?, limit} -> {items:[...], nextCursor?}

4) define services involved
   UserService        - create users, follow/unfollow.
   PostService        - create posts; like/comment; read post stats.
   GraphService       - read follow graph (who I follow).
   FeedService        - build/rank/paginate feed; small cache with TTL.
   IdGenerator        - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, username UNIQUE, created_at)
   follow(user_id FK, target_user_id FK, created_at)  UNIQUE(user_id, target_user_id)
   post(id PK, author_id FK, caption, media_url, created_at)
   like(id PK, post_id FK, user_id FK, created_at)    UNIQUE(post_id, user_id)
   comment(id PK, post_id FK, user_id FK, text, created_at)
   (feed cache not persisted: user_id -> [post_id, score, cached_at])
*/

import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/* ===== Domain ===== */
final class User { final String id, username; final Instant createdAt=Instant.now(); User(String id,String u){this.id=id;this.username=u;} }

final class Post {
    final String id, authorId, caption, mediaUrl; final Instant createdAt=Instant.now();
    final Set<String> likes = ConcurrentHashMap.newKeySet();
    final List<Comment> comments = Collections.synchronizedList(new ArrayList<>());
    Post(String id, String authorId, String caption, String mediaUrl){
        this.id=id; this.authorId=authorId; this.caption=caption; this.mediaUrl=mediaUrl;
    }
}
final class Comment { final String id, postId, userId, text; final Instant createdAt=Instant.now();
    Comment(String id,String postId,String userId,String text){this.id=id;this.postId=postId;this.userId=userId;this.text=text;}
}
final class FollowEdge { final String userId, targetUserId; final Instant createdAt=Instant.now();
    FollowEdge(String u,String t){this.userId=u;this.targetUserId=t;}
}

/* ===== Ids ===== */
class Ids { private final AtomicLong n=new AtomicLong(1); String next(String p){ return p+"-"+n.getAndIncrement(); } }

/* ===== Repos (in-memory) ===== */
class UserRepo {
    private final Map<String,User> byId = new ConcurrentHashMap<>();
    private final Map<String,String> byUsername = new ConcurrentHashMap<>();
    User save(User u){ byId.put(u.id,u); byUsername.put(u.username,u.id); return u; }
    Optional<User> byId(String id){ return Optional.ofNullable(byId.get(id)); }
    Optional<User> byUsername(String uname){ return Optional.ofNullable(byUsername.get(uname)).map(byId::get); }
}

class FollowRepo {
    // adjacency list: follower -> set of followees
    private final Map<String, Set<String>> out = new ConcurrentHashMap<>();
    boolean follow(String userId, String targetId){
        out.computeIfAbsent(userId,k->ConcurrentHashMap.newKeySet());
        return out.get(userId).add(targetId);
    }
    boolean unfollow(String userId, String targetId){
        return out.getOrDefault(userId, Set.of()).remove(targetId);
    }
    Set<String> following(String userId){
        return new HashSet<>(out.getOrDefault(userId, Set.of()));
    }
}

class PostRepo {
    private final Map<String,Post> byId = new ConcurrentHashMap<>();
    // author -> posts sorted newest first (we’ll keep as list and sort on read for simplicity)
    private final Map<String,List<Post>> byAuthor = new ConcurrentHashMap<>();

    Post save(Post p){
        byId.put(p.id,p);
        byAuthor.computeIfAbsent(p.authorId,k->Collections.synchronizedList(new ArrayList<>())).add(p);
        return p;
    }
    Optional<Post> byId(String id){ return Optional.ofNullable(byId.get(id)); }
    List<Post> byAuthors(Set<String> authorIds){
        List<Post> all = new ArrayList<>();
        for (String a: authorIds) {
            all.addAll(byAuthor.getOrDefault(a, List.of()));
        }
        // newest first
        all.sort(Comparator.comparing((Post x)->x.createdAt).reversed().thenComparing(x->x.id));
        return all;
    }
}

/* ===== Services ===== */
class UserService {
    private final UserRepo users; private final FollowRepo follows; private final Ids ids;
    UserService(UserRepo u, FollowRepo f, Ids ids){users=u;follows=f;this.ids=ids;}
    User create(String username){
        if (users.byUsername(username).isPresent()) throw new RuntimeException("username taken");
        return users.save(new User(ids.next("u"), username));
    }
    boolean follow(String userId, String target){ if (userId.equals(target)) return false; return follows.follow(userId, target); }
    boolean unfollow(String userId, String target){ return follows.unfollow(userId, target); }
    Set<String> following(String userId){ return follows.following(userId); }
}

class PostService {
    private final PostRepo posts; private final Ids ids;
    PostService(PostRepo p, Ids ids){posts=p; this.ids=ids;}
    Post create(String authorId, String caption, String mediaUrl){ return posts.save(new Post(ids.next("p"), authorId, caption, mediaUrl)); }
    int like(String postId, String userId){
        Post p = posts.byId(postId).orElseThrow(()->new RuntimeException("post not found"));
        p.likes.add(userId); return p.likes.size();
    }
    Comment comment(String postId, String userId, String text){
        Post p = posts.byId(postId).orElseThrow(()->new RuntimeException("post not found"));
        Comment c = new Comment(ids.next("c"), postId, userId, text);
        p.comments.add(c); return c;
    }
    Optional<Post> byId(String id){ return posts.byId(id); }
    List<Post> postsForAuthors(Set<String> authors){ return posts.byAuthors(authors); }
}

/* ===== Feed Cache ===== */
final class FeedEntry { final String postId; final double score; final Instant cachedAt=Instant.now(); FeedEntry(String id,double s){postId=id;score=s;} }

class FeedCache {
    // userId -> (entries sorted desc by score); plus cursor material
    private static final long TTL_SEC = 60; // small TTL
    private final Map<String, List<FeedEntry>> cache = new ConcurrentHashMap<>();
    private final Map<String, Instant> createdAt = new ConcurrentHashMap<>();

    Optional<List<FeedEntry>> get(String userId){
        Instant ts = createdAt.get(userId);
        if (ts==null) return Optional.empty();
        if (Instant.now().isAfter(ts.plusSeconds(TTL_SEC))) { invalidate(userId); return Optional.empty(); }
        return Optional.of(cache.getOrDefault(userId, List.of()));
    }
    void put(String userId, List<FeedEntry> entries){
        cache.put(userId, entries); createdAt.put(userId, Instant.now());
    }
    void invalidate(String userId){ cache.remove(userId); createdAt.remove(userId); }
}

/* ===== Feed Service ===== */
class FeedService {
    private final UserService users; private final PostService posts; private final FeedCache cache;

    FeedService(UserService u, PostService p, FeedCache cache){users=u; posts=p; this.cache=cache;}

    static final class FeedItem {
        final String postId, authorId, caption, mediaUrl;
        final Instant createdAt; final int likeCount; final int commentCount; final double score;
        FeedItem(Post p, double score){
            this.postId=p.id; this.authorId=p.authorId; this.caption=p.caption; this.mediaUrl=p.mediaUrl;
            this.createdAt=p.createdAt; this.likeCount=p.likes.size(); this.commentCount=p.comments.size(); this.score=score;
        }
        public String toString(){ return String.format("{post=%s by=%s likes=%d comments=%d score=%.2f}", postId, authorId, likeCount, commentCount, score); }
    }

    // Rank = w1 * freshness + w2 * likes + w3 * comments
    private double score(Post p){
        double hours = Math.max(0.0, Duration.between(p.createdAt, Instant.now()).toMinutes()/60.0);
        double recency = 1.0 / (1.0 + hours);               // decays with time
        double likeBoost = Math.log(1 + p.likes.size());     // diminishing returns
        double commentBoost = 1.5 * Math.log(1 + p.comments.size());
        return 0.7*recency + 0.2*likeBoost + 0.1*commentBoost;
    }

    // Build or read cached feed, then paginate by cursor (createdAt|postId).
    List<FeedItem> getFeed(String userId, String cursor, int limit){
        List<FeedEntry> entries = cache.get(userId).orElseGet(() -> {
            Set<String> authors = users.following(userId);
            if (authors.isEmpty()) authors = Set.of(userId); // fallback to self posts
            List<Post> candidates = posts.postsForAuthors(authors);
            List<FeedEntry> ranked = candidates.stream()
                    .map(p -> new FeedEntry(p.id, score(p)))
                    .sorted(Comparator.comparingDouble((FeedEntry e)->e.score).reversed()
                            .thenComparing(e->posts.byId(e.postId).get().createdAt, Comparator.reverseOrder())
                            .thenComparing(e->e.postId))
                    .collect(Collectors.toList());
            cache.put(userId, ranked);
            return ranked;
        });

        // Cursor decoding: createdAt|postId of last item returned previously.
        Instant afterCreated = null; String afterPostId = null;
        if (cursor != null && cursor.contains("|")) {
            String[] parts = cursor.split("\\|", 2);
            afterCreated = Instant.ofEpochMilli(Long.parseLong(parts[0]));
            afterPostId = parts[1];
        }

        List<FeedItem> out = new ArrayList<>();
        int collected = 0;
        for (FeedEntry e : entries) {
            Post p = posts.byId(e.postId).orElse(null);
            if (p==null) continue;
            if (afterCreated!=null){
                // skip until we pass the cursor (compare by createdAt desc then postId)
                int cmp = p.createdAt.compareTo(afterCreated);
                if (cmp==0 && p.id.equals(afterPostId)) { continue; } // exact cursor
                if (cmp>0) { // p is newer than cursor; skip because we already served it earlier (descending order)
                    continue;
                }
            }
            out.add(new FeedItem(p, e.score));
            if (++collected >= Math.max(1, limit)) break;
        }
        return out;
    }

    String nextCursor(List<FeedItem> page){
        if (page.isEmpty()) return null;
        FeedItem last = page.get(page.size()-1);
        return last.createdAt.toEpochMilli() + "|" + last.postId;
    }

    void invalidate(String userId){ cache.invalidate(userId); }
}

/* ===== Controller (API Facade) ===== */
class FeedController {
    private final UserService users; private final PostService posts; private final FeedService feed;

    FeedController(UserService u, PostService p, FeedService f){users=u;posts=p;feed=f;}

    // Users
    User postUser(String username){ return users.create(username); }
    boolean postFollow(String userId, String target){ boolean ok=users.follow(userId,target); feed.invalidate(userId); return ok; }
    boolean deleteFollow(String userId, String target){ boolean ok=users.unfollow(userId,target); feed.invalidate(userId); return ok; }

    // Posts
    Post postCreate(String authorId, String caption, String mediaUrl){ Post p=posts.create(authorId, caption, mediaUrl); feed.invalidate(authorId); return p; }
    int postLike(String postId, String userId){ int c=posts.like(postId, userId); return c; }
    Comment postComment(String postId, String userId, String text){ return posts.comment(postId, userId, text); }

    // Feed
    Map<String,Object> getFeed(String userId, String cursor, int limit){
        List<FeedService.FeedItem> items = feed.getFeed(userId, cursor, limit);
        String next = feed.nextCursor(items);
        Map<String,Object> m = new LinkedHashMap<>();
        m.put("items", items);
        m.put("nextCursor", next);
        return m;
    }
}

/* ===== Demo (tiny) ===== */
public class InstagramFeed40Min {
    public static void main(String[] args) throws InterruptedException {
        Ids ids = new Ids();
        UserRepo userRepo = new UserRepo();
        FollowRepo followRepo = new FollowRepo();
        PostRepo postRepo = new PostRepo();

        UserService userSvc = new UserService(userRepo, followRepo, ids);
        PostService postSvc = new PostService(postRepo, ids);
        FeedCache cache = new FeedCache();
        FeedService feedSvc = new FeedService(userSvc, postSvc, cache);
        FeedController api = new FeedController(userSvc, postSvc, feedSvc);

        // Users
        User alice = api.postUser("alice");
        User bob   = api.postUser("bob");
        User carol = api.postUser("carol");

        // Graph
        api.postFollow(alice.id, bob.id);
        api.postFollow(alice.id, carol.id);

        // Posts
        Post p1 = api.postCreate(bob.id, "Sunset at the beach", "http://img/1.jpg");
        Thread.sleep(10);
        Post p2 = api.postCreate(carol.id, "Coffee ☕️", null);
        Thread.sleep(10);
        Post p3 = api.postCreate(bob.id, "Morning run 5k", null);

        // Engagement to influence ranking
        api.postLike(p1.id, alice.id);
        api.postLike(p1.id, carol.id);
        api.postComment(p2.id, alice.id, "Looks great!");
        api.postLike(p3.id, alice.id);

        // Feed page 1
        Map<String,Object> page1 = api.getFeed(alice.id, null, 2);
        System.out.println("FEED page1: " + page1.get("items"));
        String cursor = (String) page1.get("nextCursor");

        // Feed page 2
        Map<String,Object> page2 = api.getFeed(alice.id, cursor, 2);
        System.out.println("FEED page2: " + page2.get("items"));
    }
}
```

## Meeting Scheduler

```
/*
Template ->
1) define functional requirements
   - Schedule meetings between participants with date/time/duration.
   - Check participants’ availability across their calendars.
   - Book meeting room/resource if needed.
   - Update/cancel meeting, notify attendees.
   - Query list of meetings for a user.
   - In-memory, concurrency-light, simple design for 40-min interview.

2) define entities / actors
   Actors: User, CalendarService (integration stub)
   Entities: User, Meeting, MeetingRoom, Invitation

3) define apis - get/post/put, request, response
   GET  /users/{id}/meetings?day=2025-08-21
        -> [{meetingId, start, end, participants}]
   POST /meetings
        {organizerId, participantIds:[...], start, end, roomId?}
        -> {meetingId, status}
   PUT  /meetings/{id}
        {start?, end?, roomId?} -> {status}
   DELETE /meetings/{id}
        -> {status}
   POST /meetings/{id}/cancel
        -> {status}

4) define services involved
   AvailabilityService  - check if users/rooms free in requested slot.
   MeetingService       - create/update/cancel meetings.
   NotificationService  - (stub) notify participants.
   RoomService          - manage meeting rooms.
   IdGenerator          - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, email)
   meeting(id PK, organizer_id FK, start_at, end_at, room_id FK NULL, status)
   meeting_participant(meeting_id FK, user_id FK, response ENUM)
   meeting_room(id PK, name, capacity)
*/
```

### Java Implementation

```java
/*
Template ->
1) define functional requirements
   - Schedule meetings between participants with date/time/duration.
   - Check participants’ availability across their calendars.
   - Book meeting room/resource if needed.
   - Update/cancel meeting, notify attendees.
   - Query list of meetings for a user.
   - In-memory, concurrency-light, simple design for 40-min interview.

2) define entities / actors
   Actors: User, CalendarService (integration stub)
   Entities: User, Meeting, MeetingRoom, Invitation

3) define apis - get/post/put, request, response
   GET  /users/{id}/meetings?day=2025-08-21
        -> [{meetingId, start, end, participants}]
   POST /meetings
        {organizerId, participantIds:[...], start, end, roomId?}
        -> {meetingId, status}
   PUT  /meetings/{id}
        {start?, end?, roomId?} -> {status}
   DELETE /meetings/{id}
        -> {status}
   POST /meetings/{id}/cancel
        -> {status}

4) define services involved
   AvailabilityService  - check if users/rooms free in requested slot.
   MeetingService       - create/update/cancel meetings.
   NotificationService  - (stub) notify participants.
   RoomService          - manage meeting rooms.
   IdGenerator          - generate IDs.

5) define db schema - what all tables are required, what are the columns, what are the keys
   user(id PK, name, email)
   meeting(id PK, organizer_id FK, start_at, end_at, room_id FK NULL, status)
   meeting_participant(meeting_id FK, user_id FK, response ENUM)
   meeting_room(id PK, name, capacity)
*/

import java.time.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/* ===== Domain ===== */
enum MeetingStatus { SCHEDULED, CANCELLED }

final class User { final String id, name, email; User(String id,String n,String e){this.id=id;name=n;email=e;} }
final class MeetingRoom { final String id, name; final int capacity; MeetingRoom(String id,String n,int c){this.id=id;name=n;capacity=c;} }
final class Meeting {
    final String id, organizerId; final Set<String> participants; final String roomId;
    volatile LocalDateTime start, end; volatile MeetingStatus status=MeetingStatus.SCHEDULED;
    Meeting(String id,String org,Set<String> parts,LocalDateTime s,LocalDateTime e,String roomId){
        this.id=id;this.organizerId=org;this.participants=parts;this.start=s;this.end=e;this.roomId=roomId;
    }
}

/* ===== Repos ===== */
class Ids { private final AtomicLong n=new AtomicLong(1); String next(String p){return p+"-"+n.getAndIncrement();} }
class UserRepo { final Map<String,User> m=new ConcurrentHashMap<>(); User save(User u){m.put(u.id,u);return u;} Optional<User> byId(String id){return Optional.ofNullable(m.get(id));} }
class RoomRepo { final Map<String,MeetingRoom> m=new ConcurrentHashMap<>(); MeetingRoom save(MeetingRoom r){m.put(r.id,r);return r;} Optional<MeetingRoom> byId(String id){return Optional.ofNullable(m.get(id));} }
class MeetingRepo {
    final Map<String,Meeting> m=new ConcurrentHashMap<>();
    Meeting save(Meeting x){m.put(x.id,x);return x;}
    Optional<Meeting> byId(String id){return Optional.ofNullable(m.get(id));}
    List<Meeting> byUserAndDay(String uid, LocalDate d){
        return m.values().stream()
            .filter(mt->mt.participants.contains(uid) || mt.organizerId.equals(uid))
            .filter(mt->mt.start.toLocalDate().equals(d))
            .collect(Collectors.toList());
    }
}

/* ===== Services ===== */
class AvailabilityService {
    private final MeetingRepo meetings;
    AvailabilityService(MeetingRepo m){meetings=m;}
    boolean isUserAvailable(String uid, LocalDateTime s, LocalDateTime e){
        return meetings.m.values().stream()
            .filter(mt->(mt.participants.contains(uid) || mt.organizerId.equals(uid)) && mt.status==MeetingStatus.SCHEDULED)
            .noneMatch(mt->overlap(mt.start, mt.end, s, e));
    }
    private boolean overlap(LocalDateTime s1, LocalDateTime e1, LocalDateTime s2, LocalDateTime e2){
        return !e1.isBefore(s2) && !e2.isBefore(s1);
    }
}
class MeetingService {
    private final MeetingRepo meetings; private final AvailabilityService avail; private final Ids ids;
    MeetingService(MeetingRepo m, AvailabilityService a, Ids ids){meetings=m;avail=a;this.ids=ids;}
    Meeting schedule(String org, Set<String> parts, LocalDateTime s, LocalDateTime e, String roomId){
        // check availability
        if (!avail.isUserAvailable(org,s,e)) throw new RuntimeException("Organizer busy");
        for (String u: parts) if (!avail.isUserAvailable(u,s,e)) throw new RuntimeException("User busy: "+u);
        Meeting mt = new Meeting(ids.next("mt"), org, parts, s, e, roomId);
        return meetings.save(mt);
    }
    Meeting update(String id, LocalDateTime ns, LocalDateTime ne, String roomId){
        Meeting mt = meetings.byId(id).orElseThrow(()->new RuntimeException("not found"));
        mt.start=ns!=null?ns:mt.start; mt.end=ne!=null?ne:mt.end;
        mt.status=MeetingStatus.SCHEDULED;
        return meetings.save(mt);
    }
    void cancel(String id){
        meetings.byId(id).ifPresent(mt->mt.status=MeetingStatus.CANCELLED);
    }
}

/* ===== Controller Facade ===== */
class MeetingController {
    private final MeetingService service; private final MeetingRepo repo;
    MeetingController(MeetingService s, MeetingRepo r){service=s;repo=r;}
    List<Meeting> getUserMeetings(String uid, LocalDate d){ return repo.byUserAndDay(uid,d); }
    Meeting postMeeting(String org, Set<String> parts, LocalDateTime s, LocalDateTime e, String roomId){ return service.schedule(org,parts,s,e,roomId); }
    Meeting putMeeting(String id, LocalDateTime ns, LocalDateTime ne, String roomId){ return service.update(id,ns,ne,roomId); }
    void deleteMeeting(String id){ service.cancel(id); }
}

/* ===== Demo ===== */
public class MeetingScheduler40Min {
    public static void main(String[] args) {
        Ids ids = new Ids();
        UserRepo users = new UserRepo();
        RoomRepo rooms = new RoomRepo();
        MeetingRepo meetings = new MeetingRepo();
        AvailabilityService avail = new AvailabilityService(meetings);
        MeetingService svc = new MeetingService(meetings, avail, ids);
        MeetingController api = new MeetingController(svc, meetings);

        User u1 = users.save(new User(ids.next("u"), "Alice","a@x.com"));
        User u2 = users.save(new User(ids.next("u"), "Bob","b@x.com"));
        rooms.save(new MeetingRoom(ids.next("room"), "Conf A", 6));

        Meeting m1 = api.postMeeting(u1.id, Set.of(u2.id), LocalDateTime.now().plusHours(1), LocalDateTime.now().plusHours(2), null);
        System.out.println("Scheduled meeting: "+m1.id+" participants="+m1.participants);

        System.out.println("Meetings for Bob today: "+api.getUserMeetings(u2.id, LocalDate.now()));

        api.deleteMeeting(m1.id);
        System.out.println("Cancelled meeting. Status="+meetings.byId(m1.id).get().status);
    }
}
```