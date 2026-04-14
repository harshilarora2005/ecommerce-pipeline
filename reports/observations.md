# Initial Dataset Observations

## Tables Loaded

* orders
* order_items
* customers

## Shape Summary

* Orders table contains order-level transaction records
* Order items table contains product-level entries per order
* Customers table contains customer location identifiers

## Key Join Columns Identified

* `order_id` links orders ↔ order_items
* `customer_id` links orders ↔ customers

## Datatype Observations

* Timestamp columns in orders are currently stored as object datatype
* Numeric columns in order_items appear ready for aggregation

## Missing Values

* Orders table contains null values in delivery-related columns
* These nulls likely correspond to undelivered or cancelled orders

## Immediate ETL Implications

* Timestamp conversion is required before delivery analysis
* Null handling strategy must be decided before feature engineering
* Join integrity should be checked before building master table

## Derived Features Created

* `delivery_days` calculated from purchase to delivery date
* `is_late` created by comparing actual delivery date with estimated delivery date

## Cleaning Progress

* Timestamp columns converted successfully to datetime format
* Cleaned orders table exported to processed folder

## First Join Completed

* Orders table successfully joined with order_items using `order_id`
* Row count increased as expected due to one-to-many relationship

## Join Validation

* Repeated order_id values observed for multi-item orders
* Price and freight columns now available for order-level enrichment

## Customer Join Completed

* Customer information successfully merged using `customer_id`
* Geographic fields now available for regional analysis

## New Analytical Possibilities

* Revenue by city and state
* Delivery performance by region
* Customer concentration analysis


## Missing Product Metadata

* `product_category_name` contains 1603 missing values after product merge
* Sales rows were preserved using left join
* Missing category labels will need treatment before category-level analysis
